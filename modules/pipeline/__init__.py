"""ScreenMate pipeline layer.

Pipelines are the only place where business logic lives.  Routes delegate
to pipelines; pipelines orchestrate providers, context, logging, and
telemetry.  This keeps routes thin and testable.
"""
