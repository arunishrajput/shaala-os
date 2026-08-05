import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../core/ws_client.dart';
import '../data/models/auth_result.dart';
import '../data/repositories.dart';

class AuthState {
  const AuthState({this.result, this.loading = false, this.error});

  final AuthResult? result;
  final bool loading;
  final String? error;

  bool get isLoggedIn => result != null;
}

/// Manual Riverpod Notifier — no @riverpod codegen anywhere in this app
/// (PROMPT.md §3, §7.3).
class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthState();

  Future<void> demoLogin(String role) async {
    state = AuthState(loading: true, result: state.result);
    try {
      final result = await ref.read(authRepositoryProvider).demoLogin(role);
      state = AuthState(result: result);
    } on DioException catch (e) {
      state = AuthState(error: ApiException.fromDioException(e).message);
    }
  }

  void logout() => state = const AuthState();
}

final authProvider = NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(tokenProvider: () => ref.read(authProvider).result?.accessToken);
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider));
});

final peopleRepositoryProvider = Provider<PeopleRepository>((ref) {
  return PeopleRepository(ref.watch(apiClientProvider));
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
