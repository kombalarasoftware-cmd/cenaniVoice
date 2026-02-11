FROM dpage/pgadmin4:latest

# Copy pgpassfile with correct permissions for auto-login
COPY pgpassfile /tmp/.pgpass
USER root
RUN chmod 600 /tmp/.pgpass && chown 5050:5050 /tmp/.pgpass
USER pgadmin

ENV PGPASSFILE=/tmp/.pgpass
