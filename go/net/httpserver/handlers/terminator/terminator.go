package terminator

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
	mux        *http.ServeMux
	logger     *zap.SugaredLogger
	shutdowner fx.Shutdowner
}

// New http handler
func New(mux *http.ServeMux, logger *zap.SugaredLogger, shutdowner fx.Shutdowner) *Handler {
	h := Handler{mux, logger, shutdowner}
	h.registerRoutes()

	return &h
}

// RegisterRoutes for all http endpoints
func (h *Handler) registerRoutes() {
	h.logger.Info("Registering handler on /quitquitquit")
	h.mux.HandleFunc("/quitquitquit", h.HealthCheck)
}

func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.logger.Info(r)
	w.WriteHeader(200)
	w.Write([]byte("This server is going down!"))
	h.shutdowner.Shutdown()
}
