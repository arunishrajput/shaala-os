import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/notification.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final notificationsRepositoryProvider = Provider<NotificationsRepository>((ref) {
  return NotificationsRepository(ref.watch(apiClientProvider));
});

/// The Outbox (PROMPT.md §6.3): self-invalidates on notifications.updated,
/// broadcast whenever a substitute assignment or a "draft parent messages"
/// tap creates new rows.
class NotificationsNotifier extends AsyncNotifier<List<NotificationModel>> {
  @override
  Future<List<NotificationModel>> build() {
    ref.listen(eventStreamProvider, (_, next) {
      if (next.value?.type == 'notifications.updated') ref.invalidateSelf();
    });
    return ref.read(notificationsRepositoryProvider).fetch();
  }
}

final notificationsProvider =
    AsyncNotifierProvider<NotificationsNotifier, List<NotificationModel>>(
      NotificationsNotifier.new,
    );
