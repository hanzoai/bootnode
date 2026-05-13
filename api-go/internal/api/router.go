// Package api — HTTP router wiring.
package api

import (
	"context"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"github.com/hanzoai/bootnode/internal/config"
	"github.com/hanzoai/bootnode/internal/db"
	"github.com/hanzoai/bootnode/internal/iam"
)

// Deps bundles the runtime collaborators every route handler may need.
// Routers receive Deps at registration time; per-request injection
// flows through r.Context() (Claims, request id).
type Deps struct {
	Pool   *db.Pool
	IAM    iam.Verifier
	Config *config.Settings
}

// New builds the root chi router with middleware + every mounted route
// package. Mounting order is stable; new route packages append at the
// bottom of the section they belong to.
func New(deps Deps) http.Handler {
	r := chi.NewRouter()

	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60_000_000_000)) // 60s
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   allowedOrigins(deps.Config),
		AllowedMethods:   []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Authorization", "Content-Type", "X-Api-Key", "X-Request-Id"},
		ExposedHeaders:   []string{"X-Request-Id"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	r.Get("/healthz", healthz)
	r.Get("/readyz", readyz(deps))

	r.Route(deps.Config.APIPrefix, func(v1 chi.Router) {
		// Public auth routes.
		v1.Mount("/auth", AuthRouter(deps))

		// Authenticated routes.
		v1.Group(func(authed chi.Router) {
			authed.Use(iam.Middleware(deps.IAM))
			authed.Mount("/chains", ChainsRouter(deps))
			authed.Mount("/projects", ProjectsRouter(deps))
			authed.Mount("/api-keys", APIKeysRouter(deps))
			authed.Mount("/wallets", WalletsRouter(deps))
			authed.Mount("/webhooks", WebhooksRouter(deps))
			authed.Mount("/rpc", RPCRouter(deps))
			authed.Mount("/tokens", TokensRouter(deps))
			authed.Mount("/nfts", NFTsRouter(deps))
		})
	})

	return r
}

func allowedOrigins(cfg *config.Settings) []string {
	out := []string{cfg.FrontendURL}
	out = append(out, cfg.AllowedOrigins...)
	return out
}

func healthz(w http.ResponseWriter, _ *http.Request) {
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func readyz(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2_000_000_000) // 2s
		defer cancel()
		if err := deps.Pool.Ping(ctx); err != nil {
			http.Error(w, `{"status":"degraded","error":"db unreachable"}`, http.StatusServiceUnavailable)
			return
		}
		_, _ = w.Write([]byte(`{"status":"ready"}`))
	}
}
