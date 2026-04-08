package health

import (
	"net/http"

	"go.uber.org/fx"
	"go.uber.org/zap"
)

var Module = fx.Options(
	fx.Invoke(New),
)

// Handler for http requests
type Handler struct {
	mux    *http.ServeMux
	logger *zap.SugaredLogger
}

// New http handler
func New(s *http.ServeMux, l *zap.SugaredLogger) *Handler {
	h := Handler{s, l}
	h.registerRoutes()

	return &h
}

// RegisterRoutes for all http endpoints
func (h *Handler) registerRoutes() {
	h.logger.Info("Registering handler on /healthz")
	h.mux.HandleFunc("/healthz", h.HealthCheck)
}

func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.logger.Info(r)
	w.WriteHeader(200)
	w.Write([]byte("OK"))
}
