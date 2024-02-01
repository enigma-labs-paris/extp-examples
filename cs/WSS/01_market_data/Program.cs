using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace WebSocketExample
{
    public class WebSocketClient
    {
        private const string EXTP_WSS = "wss://staging-extp.enigma-securities.io/ws";
        private const string API_TOKEN = "<YOUR_API_KEY>";
        private static readonly string[] DEFAULT_SUBSCRIPTIONS = { "BTC-USD", "ETH-USD", "LTC-USD" };

        private enum WS_ACTION
        {
            SUBSCRIBE = 1,
            UNSUBSCRIBE = 2,
            ORDER = 3,
            AUTH = 4
        }

        private enum WS_ORDER_TYPE
        {
            MARKET = 1,
            MARKET_NOMINAL = 2,
            LIMIT = 3
        }

        private enum WS_ORDER_SIDE
        {
            BUY = 1,
            SELL = 2
        }

        private enum WS_SUB_TYPE
        {
            MARKET_DATA = 1,
            ORDER_UPDATES = 2
        }

        private static async Task Authorize(ClientWebSocket ws)
        {
            Console.WriteLine("Authenticating...");
            var authMessage = new { type = WS_ACTION.AUTH, auth_token = API_TOKEN };
            var authJson = JsonSerializer.Serialize(authMessage);
            await SendWebSocketMessage(ws, authJson);
        }

        private static async Task SubscribeMarketData(ClientWebSocket ws, IEnumerable<string> instruments)
        {
            var subscriptions = new List<object>();
            foreach (var instrument in instruments)
            {
                var subscription = new
                {
                    type = WS_SUB_TYPE.MARKET_DATA,
                    instrument,
                    provider = "aggregated"
                };
                subscriptions.Add(subscription);
            }

            var subscribeMessage = new { type = WS_ACTION.SUBSCRIBE, subscriptions };
            var subscribeJson = JsonSerializer.Serialize(subscribeMessage);
            await SendWebSocketMessage(ws, subscribeJson);
        }

        private static async Task SendWebSocketMessage(ClientWebSocket ws, string message)
        {
            var encodedMessage = Encoding.UTF8.GetBytes(message);
            var buffer = new ArraySegment<byte>(encodedMessage, 0, encodedMessage.Length);
            await ws.SendAsync(buffer, WebSocketMessageType.Text, true, CancellationToken.None);
        }

        private static async Task ReceiveWebSocketMessages(ClientWebSocket ws)
        {
            while (true)
            {
                var buffer = new ArraySegment<byte>(new byte[8192]);
                var result = await ws.ReceiveAsync(buffer, CancellationToken.None);

                if (result.MessageType == WebSocketMessageType.Text)
                {
                    var message = Encoding.UTF8.GetString(buffer.Array, 0, result.Count);
                    Console.WriteLine(message);
                }
                else if (result.MessageType == WebSocketMessageType.Close)
                {
                    Console.WriteLine("WebSocket connection closed.");
                    break;
                }
            }
        }

        private static async Task WebSocketRun()
        {

            using var ws = new ClientWebSocket();
            await ws.ConnectAsync(new Uri(EXTP_WSS), CancellationToken.None);

            // First, authenticate on the WebSocket.
            await Authorize(ws);

            // Then, subscribe to some instruments (DEFAULT_SUBSCRIPTIONS list).
            await SubscribeMarketData(ws, DEFAULT_SUBSCRIPTIONS);

            // Finally, receive the stream and display the output on the console.
            await ReceiveWebSocketMessages(ws);
        }

        public static void Main()
        {
            System.Net.ServicePointManager.SecurityProtocol = System.Net.SecurityProtocolType.Tls12 | System.Net.SecurityProtocolType.Tls11 | System.Net.SecurityProtocolType.Tls;
            System.Net.ServicePointManager.ServerCertificateValidationCallback = delegate { return true; };
            Task.Run(WebSocketRun).Wait();
        }
    }
}