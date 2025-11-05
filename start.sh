#!/bin/bash
uvicorn asistente_termasgroup:app --host 0.0.0.0 --port=$PORT
