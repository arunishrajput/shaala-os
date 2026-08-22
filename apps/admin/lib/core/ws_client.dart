import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'env.dart';

class AppEvent {
  const AppEvent({required this.type, required this.payload});

  factory AppEvent.fromJson(Map<String, dynamic> json) {
    return AppEvent(
      type: json['type'] as String,
      payload: (json['payload'] as Map?)?.cast<String, dynamic>() ?? const {},
    );
  }

  final String type;
  final Map<String, dynamic> payload;
}

/// One WebSocket connection to /ws/events — the single source of truth for
/// "something changed" (PROMPT.md §7.3). Domain providers listen to
/// eventStreamProvider and invalidate themselves; this class only owns the
/// socket lifecycle and decoding.
class WsClient {
  WsClient({String? Function()? tokenProvider}) : _tokenProvider = tokenProvider {
    _connect();
  }

  final String? Function()? _tokenProvider;
  WebSocketChannel? _channel;
  final _controller = StreamController<AppEvent>.broadcast();
  final _statusController = StreamController<bool>.broadcast();

  Stream<AppEvent> get events => _controller.stream;

  // A dedicated status stream, not derived from `events`: reconnects here are
  // silent (onDone/onError just retry), so a "has the event stream ever
  // emitted anything" check would latch "Live" forever after the first
  // message and never reflect a later drop.
  Stream<bool> get connectionStatus => _statusController.stream;

  Future<void> _connect() async {
    // The server requires ?token=<jwt> on the handshake. Read it fresh on
    // every (re)connect — not just once at construction — so a login that
    // happens after this client is built, or a token refresh, is picked up
    // without needing to tear down and recreate the whole client.
    final token = _tokenProvider?.call();
    if (token == null) {
      _statusController.add(false);
      _scheduleReconnect();
      return;
    }
    final channel = WebSocketChannel.connect(
      Uri.parse('${Env.wsBaseUrl}/ws/events').replace(
        queryParameters: {'token': token},
      ),
    );
    _channel = channel;
    try {
      await channel.ready;
    } catch (_) {
      _statusController.add(false);
      _scheduleReconnect();
      return;
    }
    _statusController.add(true);
    channel.stream.listen(
      (raw) {
        try {
          final decoded = jsonDecode(raw as String) as Map<String, dynamic>;
          _controller.add(AppEvent.fromJson(decoded));
        } catch (_) {
          // Malformed frame — ignore, don't crash the stream.
        }
      },
      onDone: () {
        _statusController.add(false);
        _scheduleReconnect();
      },
      onError: (_) {
        _statusController.add(false);
        _scheduleReconnect();
      },
      cancelOnError: true,
    );
  }

  void _scheduleReconnect() {
    Future.delayed(const Duration(seconds: 3), _connect);
  }

  void dispose() {
    _channel?.sink.close();
    _controller.close();
    _statusController.close();
  }
}
