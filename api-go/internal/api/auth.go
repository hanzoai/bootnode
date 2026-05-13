// Package api — auth routes (local email/password + OAuth callback).
package api

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"golang.org/x/crypto/bcrypt"

	"github.com/hanzoai/bootnode/internal/db"
)

// AuthRouter mounts /auth/* routes.
func AuthRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Post("/login", login(deps))
	r.Post("/signup", signup(deps))
	r.Post("/refresh", refresh(deps))
	return r
}

type loginReq struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}
type loginResp struct {
	Token   string    `json:"token"`
	Expires time.Time `json:"expires"`
	User    userView  `json:"user"`
}
type userView struct {
	ID    string `json:"id"`
	Email string `json:"email"`
	Name  string `json:"name"`
}

func login(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var in loginReq
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "invalid body")
			return
		}
		in.Email = strings.ToLower(strings.TrimSpace(in.Email))
		if in.Email == "" || in.Password == "" {
			writeErr(w, http.StatusBadRequest, "email + password required")
			return
		}

		u, err := findUserByEmail(r.Context(), deps.Pool, in.Email)
		if err != nil {
			if errors.Is(err, pgx.ErrNoRows) {
				writeErr(w, http.StatusUnauthorized, "invalid credentials")
				return
			}
			writeErr(w, http.StatusInternalServerError, "db error")
			return
		}
		if u.PasswordHash == nil || bcrypt.CompareHashAndPassword([]byte(*u.PasswordHash), []byte(in.Password)) != nil {
			writeErr(w, http.StatusUnauthorized, "invalid credentials")
			return
		}

		tok, exp, err := issueJWT(deps, u)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "sign error")
			return
		}
		_, _ = deps.Pool.Exec(r.Context(), `UPDATE users SET last_login_at = NOW() WHERE id = $1`, u.ID)

		_ = json.NewEncoder(w).Encode(loginResp{
			Token: tok, Expires: exp,
			User: userView{ID: u.ID.String(), Email: u.Email, Name: u.Name},
		})
	}
}

type signupReq struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Name     string `json:"name"`
}

func signup(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var in signupReq
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "invalid body")
			return
		}
		in.Email = strings.ToLower(strings.TrimSpace(in.Email))
		if in.Email == "" || in.Password == "" || in.Name == "" {
			writeErr(w, http.StatusBadRequest, "email + password + name required")
			return
		}
		if len(in.Password) < 8 {
			writeErr(w, http.StatusBadRequest, "password must be >=8 chars")
			return
		}
		hash, err := bcrypt.GenerateFromPassword([]byte(in.Password), bcrypt.DefaultCost)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "hash error")
			return
		}
		id := uuid.New()
		_, err = deps.Pool.Exec(r.Context(),
			`INSERT INTO users (id, email, name, password_hash) VALUES ($1, $2, $3, $4)`,
			id, in.Email, in.Name, string(hash))
		if err != nil {
			if strings.Contains(err.Error(), "duplicate") {
				writeErr(w, http.StatusConflict, "email already registered")
				return
			}
			writeErr(w, http.StatusInternalServerError, "db error")
			return
		}
		u := &db.User{ID: id, Email: in.Email, Name: in.Name}
		tok, exp, _ := issueJWT(deps, u)
		_ = json.NewEncoder(w).Encode(loginResp{
			Token: tok, Expires: exp,
			User: userView{ID: u.ID.String(), Email: u.Email, Name: u.Name},
		})
	}
}

func refresh(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Refresh requires a still-valid token. Verify, then re-issue.
		token := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
		token = strings.TrimPrefix(token, "bearer ")
		if token == "" {
			writeErr(w, http.StatusUnauthorized, "missing token")
			return
		}
		claims, err := deps.IAM.Verify(r.Context(), token)
		if err != nil {
			writeErr(w, http.StatusUnauthorized, "invalid token")
			return
		}
		u, err := findUserByID(r.Context(), deps.Pool, claims.UserID)
		if err != nil {
			writeErr(w, http.StatusUnauthorized, "user not found")
			return
		}
		tok, exp, err := issueJWT(deps, u)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "sign error")
			return
		}
		_ = json.NewEncoder(w).Encode(loginResp{
			Token: tok, Expires: exp,
			User: userView{ID: u.ID.String(), Email: u.Email, Name: u.Name},
		})
	}
}

func issueJWT(deps Deps, u *db.User) (string, time.Time, error) {
	exp := time.Now().Add(deps.Config.JWTTTL())
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":   u.ID.String(),
		"email": u.Email,
		"name":  u.Name,
		"iat":   time.Now().Unix(),
		"exp":   exp.Unix(),
	})
	s, err := tok.SignedString([]byte(deps.Config.JWTSecret))
	return s, exp, err
}

func findUserByEmail(ctx context.Context, p *db.Pool, email string) (*db.User, error) {
	var u db.User
	row := p.QueryRow(ctx,
		`SELECT id, email, name, password_hash FROM users WHERE email = $1`, email)
	if err := row.Scan(&u.ID, &u.Email, &u.Name, &u.PasswordHash); err != nil {
		return nil, err
	}
	return &u, nil
}

func findUserByID(ctx context.Context, p *db.Pool, id string) (*db.User, error) {
	var u db.User
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}
	row := p.QueryRow(ctx,
		`SELECT id, email, name, password_hash FROM users WHERE id = $1`, uid)
	if err := row.Scan(&u.ID, &u.Email, &u.Name, &u.PasswordHash); err != nil {
		return nil, err
	}
	return &u, nil
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": msg})
}
