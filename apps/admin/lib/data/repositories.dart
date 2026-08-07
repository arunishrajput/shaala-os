import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';

import '../core/api_client.dart';
import 'models/action_item.dart';
import 'models/attendance_record.dart';
import 'models/auth_result.dart';
import 'models/class_section.dart';
import 'models/document.dart';
import 'models/notification.dart';
import 'models/staffing.dart';
import 'models/student.dart';
import 'models/teacher.dart';
import 'models/time_slot_info.dart';
import 'models/timetable_entry.dart';

class AuthRepository {
  AuthRepository(this._client);
  final ApiClient _client;

  Future<AuthResult> demoLogin(String role) async {
    final resp = await _client.dio.post(
      '/auth/demo-login',
      queryParameters: {'role': role},
    );
    return AuthResult.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<AuthResult> login(String email, String password) async {
    final resp = await _client.dio.post(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    return AuthResult.fromJson(resp.data as Map<String, dynamic>);
  }
}

class PeopleRepository {
  PeopleRepository(this._client);
  final ApiClient _client;

  Future<List<Teacher>> fetchTeachers() async {
    final resp = await _client.dio.get('/teachers');
    return (resp.data as List)
        .map((e) => Teacher.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<Student>> fetchStudents({int? classId}) async {
    final resp = await _client.dio.get(
      '/students',
      queryParameters: classId != null ? {'class_id': classId} : null,
    );
    return (resp.data as List)
        .map((e) => Student.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<ClassSection>> fetchClasses() async {
    final resp = await _client.dio.get('/classes');
    return (resp.data as List)
        .map((e) => ClassSection.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

class TimetableRepository {
  TimetableRepository(this._client);
  final ApiClient _client;

  Future<Map<String, dynamic>> generate({Map<String, double>? weights}) async {
    final resp = await _client.dio.post(
      '/timetable/generate',
      data: {'weights': ?weights},
    );
    return resp.data as Map<String, dynamic>;
  }

  Future<ActiveTimetable> fetchActive({int? classId, int? teacherId}) async {
    final resp = await _client.dio.get(
      '/timetable/active',
      queryParameters: {'class_id': ?classId, 'teacher_id': ?teacherId},
    );
    return ActiveTimetable.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> explain(int entryId) async {
    final resp = await _client.dio.get('/timetable/explain/$entryId');
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> validateMove(
    int entryId,
    int roomId,
    int slotId,
  ) async {
    final resp = await _client.dio.post(
      '/timetable/validate-move',
      data: {'entry_id': entryId, 'room_id': roomId, 'slot_id': slotId},
    );
    return resp.data as Map<String, dynamic>;
  }

  Future<TimetableEntry> move(int entryId, int roomId, int slotId) async {
    final resp = await _client.dio.post(
      '/timetable/move',
      data: {'entry_id': entryId, 'room_id': roomId, 'slot_id': slotId},
    );
    return TimetableEntry.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<List<TimeSlotInfo>> fetchSlots() async {
    final resp = await _client.dio.get('/timetable/slots');
    return (resp.data as List)
        .map((e) => TimeSlotInfo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> markAbsence(int teacherId) async {
    final resp = await _client.dio.post(
      '/timetable/absence',
      data: {'teacher_id': teacherId},
    );
    return resp.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> assignSubstitute({
    required int absenceId,
    required int classId,
    required int slotId,
    required int teacherId,
  }) async {
    final resp = await _client.dio.post(
      '/timetable/substitute',
      data: {
        'absence_id': absenceId,
        'class_id': classId,
        'slot_id': slotId,
        'teacher_id': teacherId,
      },
    );
    return resp.data as Map<String, dynamic>;
  }
}

class DocumentsRepository {
  DocumentsRepository(this._client);
  final ApiClient _client;

  Future<List<SampleInfo>> fetchSamples() async {
    final resp = await _client.dio.get('/documents/samples');
    return (resp.data as List)
        .map((e) => SampleInfo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<DocumentDetail> trySample(String docType) async {
    final resp = await _client.dio.post('/documents/samples/$docType');
    return DocumentDetail.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<List<DocumentSummary>> upload(List<PlatformFile> files) async {
    final form = FormData();
    for (final f in files) {
      if (f.bytes == null) continue;
      form.files.add(
        MapEntry('files', MultipartFile.fromBytes(f.bytes!, filename: f.name)),
      );
    }
    final resp = await _client.dio.post('/documents/upload', data: form);
    final list = (resp.data as Map<String, dynamic>)['documents'] as List;
    return list
        .map((e) => DocumentSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<DocumentSummary>> fetchDocuments({String? status}) async {
    final resp = await _client.dio.get(
      '/documents',
      queryParameters: {'status': ?status},
    );
    return (resp.data as List)
        .map((e) => DocumentSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<DocumentDetail> fetchDocument(int id) async {
    final resp = await _client.dio.get('/documents/$id');
    return DocumentDetail.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> commit(
    int id,
    List<({int fieldId, String correctedValue})> corrections,
  ) async {
    final resp = await _client.dio.post(
      '/documents/$id/commit',
      data: {
        'corrections': [
          for (final c in corrections)
            {'field_id': c.fieldId, 'corrected_value': c.correctedValue},
        ],
      },
    );
    return resp.data as Map<String, dynamic>;
  }

  Future<DocumentSummary> reject(int id) async {
    final resp = await _client.dio.post('/documents/$id/reject');
    return DocumentSummary.fromJson(resp.data as Map<String, dynamic>);
  }
}

class ActionsRepository {
  ActionsRepository(this._client);
  final ApiClient _client;

  Future<List<ActionItemModel>> fetchActions({String? status = 'open'}) async {
    final resp = await _client.dio.get(
      '/actions',
      queryParameters: {'status': ?status},
    );
    return (resp.data as List)
        .map((e) => ActionItemModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ActionItemModel> resolve(int id) async {
    final resp = await _client.dio.post('/actions/$id/resolve');
    return ActionItemModel.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<ActionItemModel> dismiss(int id) async {
    final resp = await _client.dio.post('/actions/$id/dismiss');
    return ActionItemModel.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<int> draftMessages(int id) async {
    final resp = await _client.dio.post('/actions/$id/draft-messages');
    return (resp.data as Map<String, dynamic>)['drafted'] as int;
  }
}

class AttendanceRepository {
  AttendanceRepository(this._client);
  final ApiClient _client;

  Future<Map<String, dynamic>> scan(String qrToken) async {
    final resp = await _client.dio.post(
      '/attendance/scan',
      data: {'qr_token': qrToken},
    );
    return resp.data as Map<String, dynamic>;
  }

  Future<AttendanceRecordModel> manual(int studentId, String status) async {
    final resp = await _client.dio.post(
      '/attendance/manual',
      data: {'student_id': studentId, 'status': status},
    );
    return AttendanceRecordModel.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<AttendanceToday> fetchToday() async {
    final resp = await _client.dio.get('/attendance/today');
    return AttendanceToday.fromJson(resp.data as Map<String, dynamic>);
  }
}

class StaffingRepository {
  StaffingRepository(this._client);
  final ApiClient _client;

  Future<StaffingForecast> fetchForecast({int days = 7}) async {
    final resp = await _client.dio.get(
      '/staffing/forecast',
      queryParameters: {'days': days},
    );
    return StaffingForecast.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<StaffingBacktest> fetchBacktest({int days = 30}) async {
    final resp = await _client.dio.get(
      '/staffing/backtest',
      queryParameters: {'days': days},
    );
    return StaffingBacktest.fromJson(resp.data as Map<String, dynamic>);
  }
}

class DemoRepository {
  DemoRepository(this._client);
  final ApiClient _client;

  Future<void> reset() async {
    await _client.dio.post(
      '/demo/reset',
      options: Options(
        sendTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
      ),
    );
  }
}

class NotificationsRepository {
  NotificationsRepository(this._client);
  final ApiClient _client;

  Future<List<NotificationModel>> fetch({int limit = 20}) async {
    final resp = await _client.dio.get(
      '/notifications',
      queryParameters: {'limit': limit},
    );
    return (resp.data as List)
        .map((e) => NotificationModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

/// Thrown on 4xx/5xx so UI code can show a plain-English message instead of a
/// raw stack trace (CLAUDE.md: never surface raw exception strings).
class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  factory ApiException.fromDioException(DioException e) {
    final detail = e.response?.data is Map
        ? (e.response?.data as Map)['detail']
        : null;
    return ApiException(
      detail?.toString() ?? e.message ?? 'Something went wrong',
    );
  }

  @override
  String toString() => message;
}

/// Most screens hand a `FutureProvider`/`AsyncNotifier` error straight to
/// `AsyncValue.when`'s `error` branch without ever catching it -- so unless
/// something converts it first, `DioException.toString()` (a multi-line,
/// technical dump) is what a judge sees on screen. Route every error branch
/// through this instead of interpolating the exception directly.
String friendlyError(Object error) {
  if (error is ApiException) return error.message;
  if (error is DioException) {
    return ApiException.fromDioException(error).message;
  }
  return 'Something went wrong.';
}
