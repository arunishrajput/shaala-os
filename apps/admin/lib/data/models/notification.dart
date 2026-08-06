import 'package:freezed_annotation/freezed_annotation.dart';

part 'notification.freezed.dart';
part 'notification.g.dart';

@freezed
class NotificationModel with _$NotificationModel {
  const factory NotificationModel({
    required int id,
    @JsonKey(name: 'to_name') required String toName,
    @JsonKey(name: 'to_phone') required String toPhone,
    required String channel,
    required String body,
    required String status,
    @JsonKey(name: 'created_at') required String createdAt,
  }) = _NotificationModel;

  factory NotificationModel.fromJson(Map<String, dynamic> json) =>
      _$NotificationModelFromJson(json);
}
