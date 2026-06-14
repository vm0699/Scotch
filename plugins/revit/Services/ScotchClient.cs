using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using ScotchRevit.Models;

namespace ScotchRevit.Services
{
    /// <summary>
    /// Minimal HTTP client for the Scotch backend (localhost:8000).
    ///
    /// Used by SyncCommand to PATCH a project with round-tripped room data.
    /// The base URL is read from %SCOTCH_API_URL% (default: http://localhost:8000).
    /// </summary>
    public class ScotchClient : IDisposable
    {
        private static readonly string _baseUrl =
            Environment.GetEnvironmentVariable("SCOTCH_API_URL")?.TrimEnd('/')
            ?? "http://localhost:8000";

        private readonly HttpClient _http;

        public ScotchClient()
        {
            _http = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(30),
            };
            _http.DefaultRequestHeaders.Accept.Add(
                new MediaTypeWithQualityHeaderValue("application/json"));
        }

        // ── Project fetch ─────────────────────────────────────────────────────

        /// <summary>
        /// GET /projects/{projectId} → ArchitectureProject.
        /// Returns null if the project is not found or the request fails.
        /// </summary>
        public ArchitectureProject? GetProject(string projectId)
        {
            try
            {
                string url = $"{_baseUrl}/projects/{projectId}";
                using var response = _http.GetAsync(url).GetAwaiter().GetResult();
                if (!response.IsSuccessStatusCode) return null;

                string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                return JsonSerializer.Deserialize<ArchitectureProject>(body, _opts);
            }
            catch
            {
                return null;
            }
        }

        // ── Project sync ──────────────────────────────────────────────────────

        /// <summary>
        /// PATCH /projects/{projectId} → sends partial or full project JSON.
        /// Returns true on 200 OK, false otherwise.
        /// </summary>
        public bool PatchProject(string projectId, object patchPayload)
        {
            try
            {
                string json = JsonSerializer.Serialize(patchPayload, _opts);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                string url = $"{_baseUrl}/projects/{projectId}";
                using var response = _http.PatchAsync(url, content).GetAwaiter().GetResult();
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }

        // ── Health ────────────────────────────────────────────────────────────

        /// <summary>
        /// Returns true if the Scotch backend is reachable (GET /health).
        /// </summary>
        public bool IsReachable()
        {
            try
            {
                using var response = _http.GetAsync($"{_baseUrl}/health").GetAwaiter().GetResult();
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }

        // ── Options singleton ─────────────────────────────────────────────────

        private static readonly JsonSerializerOptions _opts = new()
        {
            PropertyNamingPolicy        = JsonNamingPolicy.CamelCase,
            PropertyNameCaseInsensitive = true,
        };

        public void Dispose() => _http.Dispose();
    }
}
