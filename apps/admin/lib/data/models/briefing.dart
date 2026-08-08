import 'package:freezed_annotation/freezed_annotation.dart';

part 'briefing.freezed.dart';
part 'briefing.g.dart';

@freezed
class Briefing with _$Briefing {
  const factory Briefing({
    required String narrative,
    required Map<String, dynamic> stats,
    required String source,
    @JsonKey(name: 'generated_at') required String generatedAt,
  }) = _Briefing;

  factory Briefing.fromJson(Map<String, dynamic> json) =>
      _$BriefingFromJson(json);
}
