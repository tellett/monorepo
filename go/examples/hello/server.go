package hello

import (
	"example.com/monorepo/go/examples/hello/handlers/greeter"
	"example.com/monorepo/go/net/httpserver"

	"go.uber.org/fx"
)

var Module = fx.Options(
	httpserver.Module,
	greeter.Module,
)
