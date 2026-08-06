import 'package:freezed_annotation/freezed_annotation.dart';

part 'staffing.freezed.dart';
part 'staffing.g.dart';

@freezed
class StaffingDay with _$StaffingDay {
  const factory StaffingDay({
    required String date,
    @JsonKey(name: 'expected_absences') required double expectedAbsences,
    @JsonKey(name: 'expected_uncovered_periods') required double expectedUncoveredPeriods,
  }) = _StaffingDay;

  factory StaffingDay.fromJson(Map<String, dynamic> json) => _$StaffingDayFromJson(json);
}

@freezed
class DepartmentForecast with _$DepartmentForecast {
  const factory DepartmentForecast({
    required String department,
    @JsonKey(name: 'teacher_count') required int teacherCount,
    required List<StaffingDay> days,
    String? recommendation,
  }) = _DepartmentForecast;

  factory DepartmentForecast.fromJson(Map<String, dynamic> json) =>
      _$DepartmentForecastFromJson(json);
}

@freezed
class StaffingForecast with _$StaffingForecast {
  const factory StaffingForecast({
    @JsonKey(name: 'as_of') required String asOf,
    required int days,
    required List<DepartmentForecast> departments,
  }) = _StaffingForecast;

  factory StaffingForecast.fromJson(Map<String, dynamic> json) =>
      _$StaffingForecastFromJson(json);
}

@freezed
class BacktestPoint with _$BacktestPoint {
  const factory BacktestPoint({
    required String department,
    required String date,
    required double predicted,
    required int actual,
  }) = _BacktestPoint;

  factory BacktestPoint.fromJson(Map<String, dynamic> json) => _$BacktestPointFromJson(json);
}

@freezed
class StaffingBacktest with _$StaffingBacktest {
  const factory StaffingBacktest({
    required int days,
    double? mae,
    @JsonKey(name: 'naive_mae') double? naiveMae,
    @JsonKey(name: 'accuracy_pct') double? accuracyPct,
    required List<BacktestPoint> points,
  }) = _StaffingBacktest;

  factory StaffingBacktest.fromJson(Map<String, dynamic> json) =>
      _$StaffingBacktestFromJson(json);
}
