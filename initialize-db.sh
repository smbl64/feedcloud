#!/bin/bash

set -eux

python -m feedcloud database init
python -m feedcloud user create-root
