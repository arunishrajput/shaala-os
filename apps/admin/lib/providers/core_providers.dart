import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../core/ws_client.dart';
import '../data/models/auth_result.dart';
import '../data/repositories.dart';

class AuthState {
  const AuthState({this.result, this.loadingRole, this.error});

  final AuthResult? result;
  // Which of the three demo-login buttons is in flight, if any -- lets the
  // pressed button show its own spinner instead of all three just going
  // inert with no feedback that the click registered.
  final String? loadingRole;
  final String? error;

  bool get isLoggedIn => result != null;
  bool get loading => loadingRole != null;
}

/// Manual Riverpod Notifier — no @riverpod codegen anywhere in this app
/// (PROMPT.md §3, §7.3).
class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthState();

  Future<void> demoLogin(String role) async {
    state = AuthState(loadingRole: role, result: state.result);
    try {
      final result = await ref.read(authRepositoryProvider).demoLogin(role);
      state = AuthState(result: result);
    } catch (e) {
      state = AuthState(error: friendlyError(e));
    }
  }

  void logout() => state = const AuthState();
}

final authProvider = NotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    tokenProvider: () => ref.read(authProvider).result?.accessToken,
  );
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider));
});

final peopleRepositoryProvider = Provider<PeopleRepository>((ref) {
  return PeopleRepository(ref.watch(apiClientProvider));
});

final demoRepositoryProvider = Provider<DemoRepository>((ref) {
  return DemoRepository(ref.watch(apiClientProvider));
});

// The WebSocket is the single source of truth for "something changed"
// (PROMPT.md §7.3). Domain providers listen to eventStreamProvider and
// invalidate themselves once there are domain events to react to (Phase 3+).
final wsClientProvider = Provider<WsClient>((ref) {
  final client = WsClient();
  ref.onDispose(client.dispose);
  return client;
});

final eventStreamProvider = StreamProvider<AppEvent>((ref) {
  return ref.watch(wsClientProvider).events;
});

// Separate from eventStreamProvider on purpose: connectivity can change
// (drop, silently reconnect) without a single domain event ever arriving,
// and the header's "Live"/"Connecting…" badge needs to reflect that.
final wsConnectionProvider = StreamProvider<bool>((ref) {
  return ref.watch(wsClientProvider).connectionStatus;
});
