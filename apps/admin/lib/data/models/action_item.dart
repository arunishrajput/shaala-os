import 'package:freezed_annotation/freezed_annotation.dart';

part 'action_item.freezed.dart';
part 'action_item.g.dart';

@freezed
class ActionItemModel with _$ActionItemModel {
  const factory ActionItemModel({
    required int id,
    required String kind,
    required String severity,
    required String title,
    required String body,
    required Map<String, dynamic> payload,
    required String status,
    @JsonKey(name: 'created_at') required String createdAt,
    @JsonKey(name: 'resolved_at') String? resolvedAt,
    @JsonKey(name: 'primary_action') required String primaryAction,
  }) = _ActionItemModel;

  factory ActionItemModel.fromJson(Map<String, dynamic> json) =>
      _$ActionItemModelFromJson(json);
}
