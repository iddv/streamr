module github.com/iddv/streamr/node-client-go

go 1.23.4

require (
	github.com/sirupsen/logrus v1.9.3
	gopkg.in/yaml.v3 v3.0.1
	tailscale.com v1.76.6
)

require (
	github.com/stretchr/testify v1.9.0 // indirect
	golang.org/x/sys v0.20.0 // indirect
)

replace github.com/iddv/streamr/node-client-go => .
