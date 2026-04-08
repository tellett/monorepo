package httpserver

import (
	"context"
	"net/http"

	"example.com/monorepo/go/logging/loggerfx"
	"example.com/monorepo/go/net/httpserver/handlers/health"
	"example.com/monorepo/go/net/httpserver/handlers/terminator"

	"go.uber.org/fx"
	"go.uber.org/zap"
)

var Module = fx.Options(
	fx.Provide(http.NewServeMux),
	loggerfx.Module,
	health.Module,
	terminator.Module,
	fx.Invoke(registerHooks),
)

func registerHooks(
	lifecycle fx.Lifecycle, mux *http.ServeMux, logger *zap.SugaredLogger,
) {
	lifecycle.Append(
		fx.Hook{
			OnStart: func(context.Context) error {
				logger.Info("Listening on localhost:8080")
				go http.ListenAndServe(":8080", mux)
				return nil
			},
			OnStop: func(context.Context) error {
				return logger.Sync()
			},
		},
	)
}
