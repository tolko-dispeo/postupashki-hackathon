using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;

namespace Postupashki.Launcher.Services;

public sealed record CommandResult(int ExitCode, string Output)
{
    public bool Success => ExitCode == 0;
}

public sealed class DockerService
{
    private static readonly HttpClient Http = new()
    {
        Timeout = TimeSpan.FromSeconds(4),
    };

    public async Task<CommandResult> RunAsync(
        string workingDirectory,
        Action<string>? onOutput,
        CancellationToken cancellationToken,
        params string[] arguments)
    {
        var output = new StringBuilder();
        var outputLock = new object();
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = "docker",
                WorkingDirectory = workingDirectory,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
            },
            EnableRaisingEvents = true,
        };

        foreach (var argument in arguments)
        {
            process.StartInfo.ArgumentList.Add(argument);
        }

        void CaptureLine(string? line)
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                return;
            }

            lock (outputLock)
            {
                output.AppendLine(line);
            }

            onOutput?.Invoke(line);
        }

        process.OutputDataReceived += (_, eventArgs) => CaptureLine(eventArgs.Data);
        process.ErrorDataReceived += (_, eventArgs) => CaptureLine(eventArgs.Data);

        try
        {
            if (!process.Start())
            {
                return new CommandResult(-1, "Не удалось запустить команду Docker.");
            }

            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            using var registration = cancellationToken.Register(() =>
            {
                try
                {
                    if (!process.HasExited)
                    {
                        process.Kill(entireProcessTree: true);
                    }
                }
                catch
                {
                    // The process may have exited between the check and Kill().
                }
            });

            await process.WaitForExitAsync(cancellationToken);
            process.WaitForExit();

            lock (outputLock)
            {
                return new CommandResult(process.ExitCode, output.ToString().Trim());
            }
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception exception)
        {
            CaptureLine(exception.Message);
            lock (outputLock)
            {
                return new CommandResult(-1, output.ToString().Trim());
            }
        }
    }

    public Task<CommandResult> CheckCliAsync(CancellationToken cancellationToken) =>
        RunAsync(Environment.CurrentDirectory, null, cancellationToken, "--version");

    public Task<CommandResult> CheckEngineAsync(CancellationToken cancellationToken) =>
        RunAsync(
            Environment.CurrentDirectory,
            null,
            cancellationToken,
            "info",
            "--format",
            "{{.ServerVersion}}"
        );

    public static bool TryStartDockerDesktop()
    {
        var candidates = new[]
        {
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                "Docker",
                "Docker",
                "Docker Desktop.exe"
            ),
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Docker",
                "Docker Desktop.exe"
            ),
        };

        var executable = candidates.FirstOrDefault(File.Exists);
        if (executable is null)
        {
            return false;
        }

        Process.Start(new ProcessStartInfo(executable) { UseShellExecute = true });
        return true;
    }

    public static string? FindProjectDirectory()
    {
        var starts = new[] { AppContext.BaseDirectory, Environment.CurrentDirectory };
        var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var start in starts)
        {
            var directory = new DirectoryInfo(Path.GetFullPath(start));
            while (directory is not null && visited.Add(directory.FullName))
            {
                if (IsProjectDirectory(directory.FullName))
                {
                    return directory.FullName;
                }

                directory = directory.Parent;
            }
        }

        return null;
    }

    public static bool IsProjectDirectory(string directory) =>
        File.Exists(Path.Combine(directory, "compose.yaml"))
        && Directory.Exists(Path.Combine(directory, "docker"))
        && Directory.Exists(Path.Combine(directory, "frontend"))
        && Directory.Exists(Path.Combine(directory, "src"));

    public static async Task<bool> WaitForDashboardAsync(
        Action<string>? onOutput,
        CancellationToken cancellationToken
    )
    {
        var deadline = DateTimeOffset.UtcNow.AddMinutes(3);
        while (DateTimeOffset.UtcNow < deadline)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                using var response = await Http.GetAsync(
                    "http://127.0.0.1:8080/health",
                    cancellationToken
                );
                if (response.IsSuccessStatusCode)
                {
                    onOutput?.Invoke("Health-check пройден: приложение готово.");
                    return true;
                }
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                throw;
            }
            catch
            {
                // Containers can refuse connections while they are starting.
            }

            await Task.Delay(TimeSpan.FromSeconds(2), cancellationToken);
        }

        onOutput?.Invoke("Истекло время ожидания health-check.");
        return false;
    }

    public static void Open(string target)
    {
        Process.Start(new ProcessStartInfo(target) { UseShellExecute = true });
    }
}
