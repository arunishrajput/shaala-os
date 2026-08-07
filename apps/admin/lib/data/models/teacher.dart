import 'package:freezed_annotation/freezed_annotation.dart';

part 'teacher.freezed.dart';
part 'teacher.g.dart';

@freezed
class Teacher with _$Teacher {
  const factory Teacher({
    required int id,
    required String name,
    required String code,
    required List<String> subjects,
    required String dept,
    required String phone,
    @JsonKey(name: 'max_periods_per_week') required int maxPeriodsPerWeek,
    @JsonKey(name: 'max_periods_per_day') required int maxPeriodsPerDay,
  }) = _Teacher;

  factory Teacher.fromJson(Map<String, dynamic> json) =>
      _$TeacherFromJson(json);
}
