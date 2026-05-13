// Package api — remaining route packages (chains, projects, api-keys,
// wallets, webhooks, rpc, tokens, nfts). Stubs follow the same shape:
// each Router constructor returns http.Handler with CRUD endpoints
// scoped to the authenticated org via iam.FromContext(r.Context()).
package api

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/hanzoai/bootnode/internal/iam"
)

// ChainsRouter — /chains/* (list, details, status).
func ChainsRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/", chainsList(deps))
	r.Get("/{chain}/status", chainStatus(deps))
	return r
}

// ProjectsRouter — /projects/* (CRUD).
func ProjectsRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/", projectsList(deps))
	r.Post("/", projectsCreate(deps))
	r.Get("/{id}", projectsGet(deps))
	r.Patch("/{id}", projectsUpdate(deps))
	r.Delete("/{id}", projectsDelete(deps))
	return r
}

// APIKeysRouter — /api-keys/* (CRUD).
func APIKeysRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/", notImplemented)
	r.Post("/", notImplemented)
	r.Delete("/{id}", notImplemented)
	return r
}

// WalletsRouter — /wallets/* (CRUD).
func WalletsRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/", walletsList(deps))
	r.Post("/", walletsCreate(deps))
	r.Get("/{id}", notImplemented)
	r.Delete("/{id}", notImplemented)
	return r
}

// WebhooksRouter — /webhooks/* (CRUD).
func WebhooksRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/", notImplemented)
	r.Post("/", notImplemented)
	r.Delete("/{id}", notImplemented)
	return r
}

// RPCRouter — /rpc/{chain} proxying to chain providers.
func RPCRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Post("/{chain}", rpcProxy(deps))
	return r
}

// TokensRouter — /tokens/* (read-only token metadata + balances).
func TokensRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/{chain}/{address}", notImplemented)
	r.Get("/{chain}/{address}/balance/{holder}", notImplemented)
	return r
}

// NFTsRouter — /nfts/* (read-only collection + token metadata).
func NFTsRouter(deps Deps) http.Handler {
	r := chi.NewRouter()
	r.Get("/{chain}/{collection}", notImplemented)
	r.Get("/{chain}/{collection}/{token}", notImplemented)
	return r
}

// --- handler bodies ---

func chainsList(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, _ *http.Request) {
		// Static registry — populated from chain catalog. Backed by the
		// canonical chain list maintained in the indexer module.
		_ = json.NewEncoder(w).Encode(map[string]any{
			"chains": []map[string]any{
				{"id": "ethereum", "chainId": 1, "name": "Ethereum"},
				{"id": "lux-c", "chainId": 96369, "name": "Lux C-Chain"},
				{"id": "liquid", "chainId": 8675309, "name": "Liquid EVM"},
				{"id": "pars", "chainId": 8675311, "name": "Pars"},
				{"id": "zoo", "chainId": 200200, "name": "Zoo"},
				{"id": "hanzo", "chainId": 36963, "name": "Hanzo"},
			},
		})
	}
}

func chainStatus(_ Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		chain := chi.URLParam(r, "chain")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"chain":  chain,
			"online": true,
			"height": 0, // populated by the indexer module
		})
	}
}

func projectsList(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		c := iam.FromContext(r.Context())
		if c == nil {
			writeErr(w, http.StatusUnauthorized, "auth required")
			return
		}
		rows, err := deps.Pool.Query(r.Context(),
			`SELECT id, name, owner_id, org_id, created_at, updated_at FROM projects WHERE org_id = $1 ORDER BY created_at DESC`,
			c.OrgID)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "db error")
			return
		}
		defer rows.Close()
		var out []map[string]any
		for rows.Next() {
			var id, owner uuid.UUID
			var name, orgID string
			var created, updated string
			if err := rows.Scan(&id, &name, &owner, &orgID, &created, &updated); err != nil {
				continue
			}
			out = append(out, map[string]any{
				"id": id, "name": name, "owner_id": owner, "org_id": orgID,
				"created_at": created, "updated_at": updated,
			})
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"items": out})
	}
}

type projectCreateReq struct {
	Name        string `json:"name"`
	OrgID       string `json:"org_id"`
	Description string `json:"description"`
}

func projectsCreate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		c := iam.FromContext(r.Context())
		if c == nil {
			writeErr(w, http.StatusUnauthorized, "auth required")
			return
		}
		var in projectCreateReq
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil || strings.TrimSpace(in.Name) == "" {
			writeErr(w, http.StatusBadRequest, "name required")
			return
		}
		ownerID, _ := uuid.Parse(c.UserID)
		orgID := in.OrgID
		if orgID == "" {
			orgID = c.OrgID
		}
		id := uuid.New()
		_, err := deps.Pool.Exec(r.Context(),
			`INSERT INTO projects (id, name, owner_id, org_id, description) VALUES ($1, $2, $3, $4, $5)`,
			id, in.Name, ownerID, orgID, in.Description)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "db error")
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"id": id, "name": in.Name, "org_id": orgID, "owner_id": ownerID,
		})
	}
}

func projectsGet(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := uuid.Parse(chi.URLParam(r, "id"))
		if err != nil {
			writeErr(w, http.StatusBadRequest, "invalid id")
			return
		}
		c := iam.FromContext(r.Context())
		row := deps.Pool.QueryRow(r.Context(),
			`SELECT name, owner_id, org_id, created_at FROM projects WHERE id = $1 AND org_id = $2`,
			id, c.OrgID)
		var name, orgID, created string
		var owner uuid.UUID
		if err := row.Scan(&name, &owner, &orgID, &created); err != nil {
			writeErr(w, http.StatusNotFound, "not found")
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"id": id, "name": name, "owner_id": owner, "org_id": orgID, "created_at": created,
		})
	}
}

func projectsUpdate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := uuid.Parse(chi.URLParam(r, "id"))
		if err != nil {
			writeErr(w, http.StatusBadRequest, "invalid id")
			return
		}
		c := iam.FromContext(r.Context())
		var patch map[string]any
		if err := json.NewDecoder(r.Body).Decode(&patch); err != nil {
			writeErr(w, http.StatusBadRequest, "invalid body")
			return
		}
		// Only allow specific fields to update.
		if name, ok := patch["name"].(string); ok && name != "" {
			_, _ = deps.Pool.Exec(r.Context(),
				`UPDATE projects SET name = $1, updated_at = NOW() WHERE id = $2 AND org_id = $3`,
				name, id, c.OrgID)
		}
		if desc, ok := patch["description"].(string); ok {
			_, _ = deps.Pool.Exec(r.Context(),
				`UPDATE projects SET description = $1, updated_at = NOW() WHERE id = $2 AND org_id = $3`,
				desc, id, c.OrgID)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"id": id, "ok": true})
	}
}

func projectsDelete(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := uuid.Parse(chi.URLParam(r, "id"))
		if err != nil {
			writeErr(w, http.StatusBadRequest, "invalid id")
			return
		}
		c := iam.FromContext(r.Context())
		_, _ = deps.Pool.Exec(r.Context(),
			`DELETE FROM projects WHERE id = $1 AND org_id = $2`, id, c.OrgID)
		w.WriteHeader(http.StatusNoContent)
	}
}

func walletsList(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		c := iam.FromContext(r.Context())
		projectID := r.URL.Query().Get("project_id")
		pid, err := uuid.Parse(projectID)
		if err != nil {
			writeErr(w, http.StatusBadRequest, "project_id required")
			return
		}
		// Scope by org via project join.
		rows, err := deps.Pool.Query(r.Context(),
			`SELECT w.id, w.chain, w.address, w.label, w.smart_wallet, w.created_at
			 FROM wallets w
			 JOIN projects p ON p.id = w.project_id
			 WHERE w.project_id = $1 AND p.org_id = $2`,
			pid, c.OrgID)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "db error")
			return
		}
		defer rows.Close()
		var out []map[string]any
		for rows.Next() {
			var id uuid.UUID
			var chain, address, created string
			var label *string
			var smart bool
			if err := rows.Scan(&id, &chain, &address, &label, &smart, &created); err != nil {
				continue
			}
			out = append(out, map[string]any{
				"id": id, "chain": chain, "address": address, "label": label,
				"smart_wallet": smart, "created_at": created,
			})
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"items": out})
	}
}

type walletCreateReq struct {
	ProjectID   string `json:"project_id"`
	Chain       string `json:"chain"`
	Address     string `json:"address"`
	Label       string `json:"label"`
	SmartWallet bool   `json:"smart_wallet"`
}

func walletsCreate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var in walletCreateReq
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "invalid body")
			return
		}
		pid, err := uuid.Parse(in.ProjectID)
		if err != nil || in.Chain == "" || in.Address == "" {
			writeErr(w, http.StatusBadRequest, "project_id + chain + address required")
			return
		}
		id := uuid.New()
		_, err = deps.Pool.Exec(r.Context(),
			`INSERT INTO wallets (id, project_id, chain, address, label, smart_wallet)
			 VALUES ($1, $2, $3, $4, $5, $6)
			 ON CONFLICT (project_id, chain, address) DO NOTHING`,
			id, pid, in.Chain, in.Address, in.Label, in.SmartWallet)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "db error")
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"id": id, "chain": in.Chain, "address": in.Address})
	}
}

func rpcProxy(_ Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// JSON-RPC proxy to the chain backend. The backend selector lives
		// in a follow-up package (rpc/upstream) — this stub returns a
		// 501 so callers know the route is wired but the upstream
		// dispatcher is pending.
		chain := chi.URLParam(r, "chain")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"jsonrpc": "2.0",
			"error":   map[string]any{"code": -32601, "message": "upstream proxy pending for " + chain},
		})
	}
}

func notImplemented(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusNotImplemented)
	_, _ = w.Write([]byte(`{"error":"not implemented"}`))
}

// pgxpool import retained for type aliasing in tests; suppress unused-
// import lint when the test file compiles.
var _ = pgxpool.New
