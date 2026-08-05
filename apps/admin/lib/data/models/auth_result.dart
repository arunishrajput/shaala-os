import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_result.freezed.dart';
part 'auth_result.g.dart';

@freezed
class AuthResult with _$AuthResult {
  const factory AuthResult({
    @JsonKey(name: 'access_token') required String accessToken,
    @JsonKey(name: 'token_type') required String tokenType,
    required String role,
    @JsonKey(name: 'user_id') required int userId,
    @JsonKey(name: 'linked_id') int? linkedId,
  }) = _AuthResult;

  factory AuthResult.fromJson(Map<String, dynamic> json) => _$AuthResultFromJson(json);
}
