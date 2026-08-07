import 'package:dio/dio.dart';

import 'env.dart';

/// Thin Dio wrapper. Domain-specific calls live in data/repositories.dart —
/// this class only owns the HTTP transport and auth header injection.
class ApiClient {
  ApiClient({String? Function()? tokenProvider})
    : _tokenProvider = tokenProvider {
    dio = Dio(
      BaseOptions(
        baseUrl: Env.apiBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ),
    );
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = _tokenProvider?.call();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
  }

  final String? Function()? _tokenProvider;
  late final Dio dio;
}
