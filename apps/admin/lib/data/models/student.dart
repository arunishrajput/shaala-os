import 'package:freezed_annotation/freezed_annotation.dart';

part 'student.freezed.dart';
part 'student.g.dart';

@freezed
class Student with _$Student {
  const factory Student({
    required int id,
    @JsonKey(name: 'admission_no') required String admissionNo,
    required String name,
    @JsonKey(name: 'class_id') required int classId,
    @JsonKey(name: 'roll_no') required int rollNo,
    @JsonKey(name: 'guardian_name') required String guardianName,
    @JsonKey(name: 'guardian_phone') required String guardianPhone,
    @JsonKey(name: 'qr_token') required String qrToken,
    @JsonKey(name: 'photo_url') String? photoUrl,
  }) = _Student;

  factory Student.fromJson(Map<String, dynamic> json) => _$StudentFromJson(json);
}
