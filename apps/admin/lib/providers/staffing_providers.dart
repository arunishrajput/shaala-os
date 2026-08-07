import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/staffing.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final staffingRepositoryProvider = Provider<StaffingRepository>((ref) {
  return StaffingRepository(ref.watch(apiClientProvider));
});

final staffingForecastProvider = FutureProvider.autoDispose<StaffingForecast>((
  ref,
) {
  return ref.watch(staffingRepositoryProvider).fetchForecast();
});

final staffingBacktestProvider = FutureProvider.autoDispose<StaffingBacktest>((
  ref,
) {
  return ref.watch(staffingRepositoryProvider).fetchBacktest();
});
