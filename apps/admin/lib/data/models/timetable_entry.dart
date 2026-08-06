import 'package:freezed_annotation/freezed_annotation.dart';

part 'timetable_entry.freezed.dart';
part 'timetable_entry.g.dart';

@freezed
class TimetableEntry with _$TimetableEntry {
  const factory TimetableEntry({
    required int id,
    @JsonKey(name: 'class_id') required int classId,
    @JsonKey(name: 'class_label') required String classLabel,
    @JsonKey(name: 'subject_id') required int subjectId,
    @JsonKey(name: 'subject_name') required String subjectName,
    @JsonKey(name: 'teacher_id') required int teacherId,
    @JsonKey(name: 'teacher_name') required String teacherName,
    @JsonKey(name: 'room_id') required int roomId,
    @JsonKey(name: 'room_name') required String roomName,
    @JsonKey(name: 'slot_id') required int slotId,
    required int day,
    required int period,
    @JsonKey(name: 'slot_label') required String slotLabel,
    @JsonKey(name: 'is_substitution') required bool isSubstitution,
  }) = _TimetableEntry;

  factory TimetableEntry.fromJson(Map<String, dynamic> json) =>
      _$TimetableEntryFromJson(json);
}

@freezed
class ActiveTimetable with _$ActiveTimetable {
  const factory ActiveTimetable({
    @JsonKey(name: 'version_id') int? versionId,
    String? label,
    @JsonKey(name: 'solver_stats') Map<String, dynamic>? solverStats,
    required List<TimetableEntry> entries,
  }) = _ActiveTimetable;

  factory ActiveTimetable.fromJson(Map<String, dynamic> json) =>
      _$ActiveTimetableFromJson(json);
}
