import 'package:freezed_annotation/freezed_annotation.dart';

part 'ask_answer.freezed.dart';
part 'ask_answer.g.dart';

@freezed
class AskAnswer with _$AskAnswer {
  const factory AskAnswer({
    required String query,
    String? intent,
    required String answer,
    Map<String, dynamic>? data,
    String? source,
  }) = _AskAnswer;

  factory AskAnswer.fromJson(Map<String, dynamic> json) =>
      _$AskAnswerFromJson(json);
}
