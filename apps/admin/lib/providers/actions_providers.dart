import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/action_item.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final actionsRepositoryProvider = Provider<ActionsRepository>((ref) {
  return ActionsRepository(ref.watch(apiClientProvider));
});

/// The Action Center's open cards. Self-invalidates on the WS events that can
/// change the set (PROMPT.md §7.3 pattern) -- `actions.updated` covers every
/// signal-engine tick and mutation that calls run_signals(), the two
/// action.* events cover this client's own resolve/dismiss taps landing
/// (including from another connected device).
class ActionItemsNotifier extends AsyncNotifier<List<ActionItemModel>> {
  @override
  Future<List<ActionItemModel>> build() {
    ref.listen(eventStreamProvider, (_, next) {
      final t = next.value?.type;
      if (t == 'actions.updated' ||
          t == 'action.resolved' ||
          t == 'action.dismissed') {
        ref.invalidateSelf();
      }
    });
    return ref.read(actionsRepositoryProvider).fetchActions();
  }

  Future<void> _remove(int id, Future<void> Function() call) async {
    final previous = state;
    state = AsyncData([
      for (final item in state.valueOrNull ?? const <ActionItemModel>[])
        if (item.id != id) item,
    ]);
    try {
      await call();
    } catch (_) {
      state = previous;
      rethrow;
    }
  }

  Future<void> resolve(int id) =>
      _remove(id, () => ref.read(actionsRepositoryProvider).resolve(id));

  Future<void> dismiss(int id) =>
      _remove(id, () => ref.read(actionsRepositoryProvider).dismiss(id));

  Future<void> draftMessages(int id) =>
      _remove(id, () => ref.read(actionsRepositoryProvider).draftMessages(id));
}

final actionItemsProvider =
    AsyncNotifierProvider<ActionItemsNotifier, List<ActionItemModel>>(
      ActionItemsNotifier.new,
    );

final openActionsCountProvider = Provider.autoDispose<int>((ref) {
  return ref.watch(actionItemsProvider).valueOrNull?.length ?? 0;
});
