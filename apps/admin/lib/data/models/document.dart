import 'package:freezed_annotation/freezed_annotation.dart';

part 'document.freezed.dart';
part 'document.g.dart';

@freezed
class DocumentSummary with _$DocumentSummary {
  const factory DocumentSummary({
    required int id,
    required String type,
    required String status,
    @JsonKey(name: 'uploaded_at') required String uploadedAt,
    @JsonKey(name: 'committed_at') String? committedAt,
  }) = _DocumentSummary;

  factory DocumentSummary.fromJson(Map<String, dynamic> json) =>
      _$DocumentSummaryFromJson(json);
}

@freezed
class ExtractedFieldModel with _$ExtractedFieldModel {
  const factory ExtractedFieldModel({
    required int id,
    required String name,
    required String value,
    @JsonKey(name: 'original_value') required String originalValue,
    required double confidence,
    List<double>? bbox,
    @JsonKey(name: 'was_corrected') required bool wasCorrected,
  }) = _ExtractedFieldModel;

  factory ExtractedFieldModel.fromJson(Map<String, dynamic> json) =>
      _$ExtractedFieldModelFromJson(json);
}

@freezed
class DocumentDetail with _$DocumentDetail {
  const factory DocumentDetail({
    required int id,
    required String type,
    required String status,
    @JsonKey(name: 'uploaded_at') required String uploadedAt,
    @JsonKey(name: 'committed_at') String? committedAt,
    @JsonKey(name: 'original_url') required String originalUrl,
    required List<String> warnings,
    @JsonKey(name: 'doc_type_confidence') double? docTypeConfidence,
    required List<ExtractedFieldModel> fields,
    required List<Map<String, dynamic>> rows,
  }) = _DocumentDetail;

  factory DocumentDetail.fromJson(Map<String, dynamic> json) => _$DocumentDetailFromJson(json);
}

@freezed
class SampleInfo with _$SampleInfo {
  const factory SampleInfo({
    @JsonKey(name: 'doc_type') required String docType,
    required String label,
  }) = _SampleInfo;

  factory SampleInfo.fromJson(Map<String, dynamic> json) => _$SampleInfoFromJson(json);
}
