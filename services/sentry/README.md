## Self-hosted sentry

[Docs](https://hub.docker.com/_/sentry)

```shell
> echo SENTRY_SECRET_KEY=SECRET > .env
> docker-compose run sentry sentry upgrade
> docker-compose up 
```
