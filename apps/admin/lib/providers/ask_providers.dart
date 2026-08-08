import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/ask_answer.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final askRepositoryProvider = Provider<AskRepository>((ref) {
  return AskRepository(ref.watch(apiClientProvider));
});

class AskState {
  const AskState({this.loading = false, this.answer, this.error});
  final bool loading;
  final AskAnswer? answer;
  final String? error;
}

class AskNotifier extends Notifier<AskState> {
  @override
  AskState build() => const AskState();

  Future<void> ask(String query) async {
    state = const AskState(loading: true);
    try {
      final answer = await ref.read(askRepositoryProvider).ask(query);
      state = AskState(answer: answer);
    } catch (e) {
      state = AskState(error: friendlyError(e));
    }
  }

  void clear() => state = const AskState();
}

final askProvider = NotifierProvider<AskNotifier, AskState>(AskNotifier.new);
