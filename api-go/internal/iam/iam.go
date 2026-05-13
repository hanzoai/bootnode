// Package iam — JWT verification + claim extraction. Backed by Hanzo
// IAM today; the Verifier interface lets a test stub or a different
// backend (Auth0, Keycloak) drop in.
package iam

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// Errors returned by Verify.
var (
	ErrTokenMissing = errors.New("authentication required")
	ErrTokenInvalid = errors.New("invalid token")
	ErrTokenExpired = errors.New("token expired")
)

// Claims is the JWT body Bootnode trusts. Validated server-side
// against IAM's JWKS in the production verifier; HS256 for local-dev.
type Claims struct {
	UserID    string   `json:"sub"`
	Email     string   `json:"email"`
	Name      string   `json:"name"`
	OrgID     string   `json:"org_id"`
	Roles     []string `json:"roles"`
	Scopes    []string `json:"scopes"`
	IssuedAt  int64    `json:"iat"`
	ExpiresAt int64    `json:"exp"`
	jwt.RegisteredClaims
}

// Verifier validates a bearer token.
type Verifier interface {
	Verify(ctx context.Context, token string) (*Claims, error)
}

// HSVerifier validates HS256 tokens using a shared secret. Used in
// local-dev; production uses JWKSVerifier against the IAM service.
type HSVerifier struct {
	secret    []byte
	clockSkew time.Duration
}

// NewHS constructs an HMAC verifier.
func NewHS(secret string) *HSVerifier {
	return &HSVerifier{secret: []byte(secret), clockSkew: 5 * time.Second}
}

// Verify implements Verifier.
func (h *HSVerifier) Verify(_ context.Context, token string) (*Claims, error) {
	claims := &Claims{}
	parsed, err := jwt.ParseWithClaims(token, claims, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, ErrTokenInvalid
		}
		return h.secret, nil
	}, jwt.WithLeeway(h.clockSkew))
	if err != nil {
		switch {
		case errors.Is(err, jwt.ErrTokenExpired):
			return nil, ErrTokenExpired
		default:
			return nil, ErrTokenInvalid
		}
	}
	if !parsed.Valid {
		return nil, ErrTokenInvalid
	}
	return claims, nil
}

// ExtractBearer pulls the bearer token out of an Authorization header.
func ExtractBearer(r *http.Request) (string, error) {
	h := r.Header.Get("Authorization")
	if h == "" {
		return "", ErrTokenMissing
	}
	parts := strings.SplitN(h, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
		return "", ErrTokenInvalid
	}
	if parts[1] == "" {
		return "", ErrTokenInvalid
	}
	return parts[1], nil
}

// Middleware verifies the JWT and stores Claims on the request context.
// Requests without a token short-circuit with 401; invalid + expired
// tokens get the same response shape (no information leak about which
// of the two failed).
func Middleware(v Verifier) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			tok, err := ExtractBearer(r)
			if err != nil {
				http.Error(w, `{"error":"authentication required"}`, http.StatusUnauthorized)
				return
			}
			claims, err := v.Verify(r.Context(), tok)
			if err != nil {
				http.Error(w, `{"error":"invalid token"}`, http.StatusUnauthorized)
				return
			}
			ctx := WithClaims(r.Context(), claims)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// contextKey is the unexported key type for Claims storage.
type contextKey struct{}

// WithClaims attaches claims to a context.
func WithClaims(ctx context.Context, c *Claims) context.Context {
	return context.WithValue(ctx, contextKey{}, c)
}

// FromContext returns the Claims bound by Middleware, or nil if absent.
func FromContext(ctx context.Context) *Claims {
	c, _ := ctx.Value(contextKey{}).(*Claims)
	return c
}
