// Package config — environment-driven application settings.
package config

import (
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Settings is the canonical application configuration. Loaded once at
// startup via Load() and accessed thereafter via Get().
type Settings struct {
	// Application
	AppName   string
	AppEnv    string // development | staging | production
	Debug     bool
	APIPrefix string

	// Database
	DatabaseURL   string
	DBPoolSize    int
	DBMaxOverflow int

	// Redis
	RedisURL string

	// Authentication
	JWTSecret        string
	JWTAlgorithm     string
	JWTExpireMinutes int
	APIKeySalt       string

	// Hanzo IAM
	IAMUrl          string
	IAMClientID     string
	IAMClientSecret string
	EnableMultiTenant bool
	AllowedOrgs       []string
	FrontendURL       string
	AllowedOrigins    []string

	// ZAP — Cap'n Proto RPC server
	ZAPEnabled bool
	ZAPHost    string
	ZAPPort    int

	// Observability
	OTELEndpoint   string
	OTELServiceName string
	PrometheusPort int

	// Listen
	HTTPHost string
	HTTPPort int

	// KMS
	KMSURL       string
	KMSAuthToken string
}

var (
	loaded   *Settings
	loadOnce sync.Once
)

// Load reads settings from environment variables exactly once and
// returns the snapshot. Subsequent calls return the cached value.
func Load() *Settings {
	loadOnce.Do(func() {
		loaded = &Settings{
			AppName:           env("APP_NAME", "Bootnode"),
			AppEnv:            env("APP_ENV", "development"),
			Debug:             envBool("DEBUG", false),
			APIPrefix:         env("API_PREFIX", "/v1"),
			DatabaseURL:       env("DATABASE_URL", "postgres://bootnode:bootnode@localhost:5432/bootnode?sslmode=disable"),
			DBPoolSize:        envInt("DB_POOL_SIZE", 20),
			DBMaxOverflow:     envInt("DB_MAX_OVERFLOW", 10),
			RedisURL:          env("REDIS_URL", "redis://localhost:6379/0"),
			JWTSecret:         env("JWT_SECRET", "change-me-in-production"),
			JWTAlgorithm:      env("JWT_ALGORITHM", "HS256"),
			JWTExpireMinutes:  envInt("JWT_EXPIRE_MINUTES", 60*24),
			APIKeySalt:        env("API_KEY_SALT", "change-me-in-production"),
			IAMUrl:            env("IAM_URL", "https://iam.hanzo.ai"),
			IAMClientID:       env("IAM_CLIENT_ID", ""),
			IAMClientSecret:   env("IAM_CLIENT_SECRET", ""),
			EnableMultiTenant: envBool("ENABLE_MULTI_TENANT", true),
			AllowedOrgs:       envList("ALLOWED_ORGS", []string{"hanzo", "zoo", "lux", "pars"}),
			FrontendURL:       env("FRONTEND_URL", "http://localhost:3001"),
			AllowedOrigins:    envList("ALLOWED_ORIGINS", nil),
			ZAPEnabled:        envBool("ZAP_ENABLED", true),
			ZAPHost:           env("ZAP_HOST", "0.0.0.0"),
			ZAPPort:           envInt("ZAP_PORT", 9999),
			OTELEndpoint:      env("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
			OTELServiceName:   env("OTEL_SERVICE_NAME", "bootnode"),
			PrometheusPort:    envInt("PROMETHEUS_PORT", 9090),
			HTTPHost:          env("HTTP_HOST", "0.0.0.0"),
			HTTPPort:          envInt("HTTP_PORT", 8000),
			KMSURL:            env("KMS_URL", "http://kms.hanzo.ai:8443"),
			KMSAuthToken:      env("KMS_AUTH_TOKEN", ""),
		}
	})
	return loaded
}

// Get returns the loaded settings, calling Load() if necessary.
func Get() *Settings { return Load() }

// JWTTTL returns the JWT expiration as a duration.
func (s *Settings) JWTTTL() time.Duration {
	return time.Duration(s.JWTExpireMinutes) * time.Minute
}

func env(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}

func envBool(key string, def bool) bool {
	if v, ok := os.LookupEnv(key); ok {
		switch strings.ToLower(v) {
		case "1", "true", "yes", "on":
			return true
		case "0", "false", "no", "off":
			return false
		}
	}
	return def
}

func envInt(key string, def int) int {
	if v, ok := os.LookupEnv(key); ok {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envList(key string, def []string) []string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		parts := strings.Split(v, ",")
		out := make([]string, 0, len(parts))
		for _, p := range parts {
			if p = strings.TrimSpace(p); p != "" {
				out = append(out, p)
			}
		}
		return out
	}
	return def
}
