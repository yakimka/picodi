FROM python:3.11-slim-bullseye as builder

ARG WHEEL=picodi-0.2.0-py3-none-any.whl
ENV VENV=/venv
ENV PATH="$VENV/bin:$PATH"

WORKDIR /code

RUN python -m venv $VENV

# for caching purposes in CI
# waiting for https://github.com/moby/buildkit/issues/1512
# to replace with this:
#COPY ./dist/$WHEEL ./$WHEEL
#RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
#    pip install --upgrade pip \
#    && pip install --upgrade wheel \
#    && pip install --upgrade ./$WHEEL
COPY ./dist/requirements.txt ./
RUN pip install --upgrade --no-cache-dir pip \
    && pip install --upgrade --no-cache-dir wheel \
    && pip install --upgrade --no-cache-dir -r requirements.txt

COPY ./dist/$WHEEL ./$WHEEL
RUN pip install --upgrade --no-cache-dir ./$WHEEL --no-deps


FROM python:3.11-slim-bullseye as production

RUN useradd -M appuser --uid=1000 --shell=/bin/false
USER appuser

ENV PATH="/venv/bin:$PATH"
WORKDIR /opt/app
COPY --from=builder /venv /venv

CMD ["python"]
