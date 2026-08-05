// Overridden at build/run time with --dart-define=API_BASE_URL=... and
// --dart-define=WS_BASE_URL=... for the deployed build. Defaults target the
// local docker-compose stack.
class Env {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const wsBaseUrl = String.fromEnvironment(
    'WS_BASE_URL',
    defaultValue: 'ws://localhost:8000',
  );
}
