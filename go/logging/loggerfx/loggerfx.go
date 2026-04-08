package loggerfx

import (
	"log"

	"go.uber.org/fx"
	"go.uber.org/zap"
)

// Module provided to fx
var Module = fx.Options(
	fx.Provide(New),
)

// ProvideLogger to fx
func New() *zap.SugaredLogger {
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("can't initialize zap logger: %v", err)
	}

	return logger.Sugar()
}
