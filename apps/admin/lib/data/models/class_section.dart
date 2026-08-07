import 'package:freezed_annotation/freezed_annotation.dart';

part 'class_section.freezed.dart';
part 'class_section.g.dart';

@freezed
class ClassSection with _$ClassSection {
  const factory ClassSection({
    required int id,
    required String grade,
    required String section,
    required int strength,
  }) = _ClassSection;

  factory ClassSection.fromJson(Map<String, dynamic> json) =>
      _$ClassSectionFromJson(json);

  const ClassSection._();

  String get label => '$grade-$section';
}
