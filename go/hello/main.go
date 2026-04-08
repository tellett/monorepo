package main

import (
	"example.com/monorepo/go/examples/hello"
	"go.uber.org/fx"
)

var Module = fx.Options(
	hello.Module,
)

func main() {
	fx.New(Module).Run()
}
