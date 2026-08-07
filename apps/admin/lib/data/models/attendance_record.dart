import 'package:freezed_annotation/freezed_annotation.dart';

part 'attendance_record.freezed.dart';
part 'attendance_record.g.dart';

@freezed
class AttendanceRecordModel with _$AttendanceRecordModel {
  const factory AttendanceRecordModel({
    required int id,
    @JsonKey(name: 'student_id') required int studentId,
    @JsonKey(name: 'student_name') required String studentName,
    @JsonKey(name: 'class_id') required int classId,
    required String status,
    required String method,
    @JsonKey(name: 'marked_at') required String markedAt,
    double? confidence,
  }) = _AttendanceRecordModel;

  factory AttendanceRecordModel.fromJson(Map<String, dynamic> json) =>
      _$AttendanceRecordModelFromJson(json);
}

@freezed
class AttendanceToday with _$AttendanceToday {
  const factory AttendanceToday({
    required String date,
    required int count,
    required int present,
    required List<AttendanceRecordModel> records,
  }) = _AttendanceToday;

  factory AttendanceToday.fromJson(Map<String, dynamic> json) =>
      _$AttendanceTodayFromJson(json);
}
