import 'package:dio/dio.dart';

import '../core/api_client.dart';
import 'models/auth_result.dart';
import 'models/class_section.dart';
import 'models/student.dart';
import 'models/teacher.dart';

class AuthRepository {
  AuthRepository(this._client);
  final ApiClient _client;

  Future<AuthResult> demoLogin(String role) async {
    final resp = await _client.dio.post('/auth/demo-login', queryParameters: {'role': role});
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
    return (resp.data as List).map((e) => Teacher.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Student>> fetchStudents({int? classId}) async {
    final resp = await _client.dio.get(
      '/students',
      queryParameters: classId != null ? {'class_id': classId} : null,
    );
    return (resp.data as List).map((e) => Student.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<ClassSection>> fetchClasses() async {
    final resp = await _client.dio.get('/classes');
    return (resp.data as List)
        .map((e) => ClassSection.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

/// Thrown on 4xx/5xx so UI code can show a plain-English message instead of a
/// raw stack trace (CLAUDE.md: never surface raw exception strings).
class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  factory ApiException.fromDioException(DioException e) {
    final detail = e.response?.data is Map ? (e.response?.data as Map)['detail'] : null;
    return ApiException(detail?.toString() ?? e.message ?? 'Something went wrong');
  }

  @override
  String toString() => message;
}
