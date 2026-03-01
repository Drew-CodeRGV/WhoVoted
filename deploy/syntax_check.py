#!/usr/bin/env python3
import py_compile
py_compile.compile('/opt/whovoted/deploy/batch_geocode_aws.py', doraise=True)
print("Syntax OK")
