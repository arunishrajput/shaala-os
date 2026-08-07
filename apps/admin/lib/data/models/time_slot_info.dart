import 'package:freezed_annotation/freezed_annotation.dart';

part 'time_slot_info.freezed.dart';
part 'time_slot_info.g.dart';

@freezed
class TimeSlotInfo with _$TimeSlotInfo {
  const factory TimeSlotInfo({
    required int id,
    required int day,
    required int period,
    required String label,
  }) = _TimeSlotInfo;

  factory TimeSlotInfo.fromJson(Map<String, dynamic> json) =>
      _$TimeSlotInfoFromJson(json);
}
