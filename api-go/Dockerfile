# syntax=docker/dockerfile:1.7
FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG VERSION=dev
RUN CGO_ENABLED=0 GOOS=linux \
    go build -trimpath \
    -ldflags "-s -w -X main.version=${VERSION}" \
    -o /out/bootnode ./cmd/bootnode

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/bootnode /usr/local/bin/bootnode
EXPOSE 8000
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/bootnode"]
