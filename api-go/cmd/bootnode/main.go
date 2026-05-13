// Command bootnode — HTTP server entry point.
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/hanzoai/bootnode/internal/api"
	"github.com/hanzoai/bootnode/internal/config"
	"github.com/hanzoai/bootnode/internal/db"
	"github.com/hanzoai/bootnode/internal/iam"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	slog.SetDefault(logger)

	cfg := config.Load()
	slog.Info("bootnode starting", "env", cfg.AppEnv, "version", version())

	rootCtx, rootCancel := context.WithCancel(context.Background())
	defer rootCancel()

	pool, err := db.Open(rootCtx, cfg.DatabaseURL, cfg.DBPoolSize, cfg.DBMaxOverflow)
	if err != nil {
		slog.Error("db open failed", "error", err)
		os.Exit(1)
	}
	defer pool.Close()

	if err := db.Init(rootCtx, pool); err != nil {
		slog.Error("db init failed", "error", err)
		os.Exit(1)
	}
	slog.Info("db ready")

	verifier := iam.NewHS(cfg.JWTSecret)

	handler := api.New(api.Deps{
		Pool:   pool,
		IAM:    verifier,
		Config: cfg,
	})

	addr := fmt.Sprintf("%s:%d", cfg.HTTPHost, cfg.HTTPPort)
	srv := &http.Server{
		Addr:              addr,
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      60 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		slog.Info("http listening", "addr", addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	select {
	case sig := <-sigCh:
		slog.Info("shutdown signal", "signal", sig.String())
	case err := <-errCh:
		slog.Error("http server error", "error", err)
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		slog.Error("graceful shutdown failed", "error", err)
		os.Exit(1)
	}
	slog.Info("bootnode stopped")
}

// version is filled at build time via -ldflags.
var version = func() string {
	if v := os.Getenv("BOOTNODE_VERSION"); v != "" {
		return v
	}
	return "dev"
}
