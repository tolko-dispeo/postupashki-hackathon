using System.ComponentModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;
using Postupashki.Launcher.Services;

namespace Postupashki.Launcher;

public partial class MainWindow : Window
{
    private const string DashboardUrl = "http://127.0.0.1:8080";
    private const string DocsUrl = "http://127.0.0.1:8080/docs";

    private readonly DockerService _docker = new();
    private CancellationTokenSource? _operationCancellation;
    private string? _projectDirectory;
    private LaunchMode _lastLaunchMode = LaunchMode.Normal;
    private bool _isBusy;

    public MainWindow()
    {
        InitializeComponent();
        _projectDirectory = DockerService.FindProjectDirectory();
        UpdateProjectPath();
        ShowPage(LauncherPage.Welcome);
        Closing += Window_Closing;
    }

    private async void BeginButton_Click(object sender, RoutedEventArgs e)
    {
        ShowPage(LauncherPage.Check);
        await RefreshChecksAsync();
    }

    private async void RefreshButton_Click(object sender, RoutedEventArgs e) =>
        await RefreshChecksAsync();

    private async Task RefreshChecksAsync()
    {
        if (_isBusy)
        {
            return;
        }

        _isBusy = true;
        RefreshButton.IsEnabled = false;
        ContinueButton.IsEnabled = false;
        StartDockerButton.Visibility = Visibility.Collapsed;
        InstallDockerButton.Visibility = Visibility.Collapsed;

        SetPending(ProjectStatusIcon, ProjectStatusGlyph, ProjectStatusText, "Проверяем compose.yaml");
        SetPending(DockerCliStatusIcon, DockerCliStatusGlyph, DockerCliStatusText, "Проверяем команду docker");
        SetPending(
            DockerEngineStatusIcon,
            DockerEngineStatusGlyph,
            DockerEngineStatusText,
            "Проверяем Docker Engine"
        );

        var projectReady = _projectDirectory is not null
            && DockerService.IsProjectDirectory(_projectDirectory);
        SetCheckResult(
            ProjectStatusIcon,
            ProjectStatusGlyph,
            ProjectStatusText,
            projectReady,
            "compose.yaml и компоненты проекта найдены",
            "Выберите корневую папку проекта"
        );

        CommandResult cli;
        try
        {
            using var cliCancellation = new CancellationTokenSource(TimeSpan.FromSeconds(8));
            cli = await _docker.CheckCliAsync(cliCancellation.Token);
        }
        catch (OperationCanceledException)
        {
            cli = new CommandResult(-1, "Проверка Docker превысила время ожидания");
        }
        SetCheckResult(
            DockerCliStatusIcon,
            DockerCliStatusGlyph,
            DockerCliStatusText,
            cli.Success,
            string.IsNullOrWhiteSpace(cli.Output) ? "Docker установлен" : cli.Output.Split('\n')[0],
            "Docker не найден — установите Docker Desktop"
        );
        InstallDockerButton.Visibility = cli.Success ? Visibility.Collapsed : Visibility.Visible;

        var engineReady = false;
        if (cli.Success)
        {
            CommandResult engine;
            try
            {
                using var engineCancellation = new CancellationTokenSource(TimeSpan.FromSeconds(8));
                engine = await _docker.CheckEngineAsync(engineCancellation.Token);
            }
            catch (OperationCanceledException)
            {
                engine = new CommandResult(-1, "Docker Engine не ответил вовремя");
            }
            engineReady = engine.Success;
            SetCheckResult(
                DockerEngineStatusIcon,
                DockerEngineStatusGlyph,
                DockerEngineStatusText,
                engineReady,
                string.IsNullOrWhiteSpace(engine.Output)
                    ? "Docker Engine отвечает"
                    : $"Docker Engine {engine.Output.Split('\n')[0]} готов",
                "Docker Desktop установлен, но движок ещё не запущен"
            );
            StartDockerButton.Visibility = engineReady
                ? Visibility.Collapsed
                : Visibility.Visible;
        }
        else
        {
            SetCheckResult(
                DockerEngineStatusIcon,
                DockerEngineStatusGlyph,
                DockerEngineStatusText,
                false,
                string.Empty,
                "Сначала установите Docker Desktop"
            );
        }

        ContinueButton.IsEnabled = projectReady && cli.Success && engineReady;
        RefreshButton.IsEnabled = true;
        _isBusy = false;
    }

    private async void StartDockerButton_Click(object sender, RoutedEventArgs e)
    {
        if (_isBusy)
        {
            return;
        }

        if (!DockerService.TryStartDockerDesktop())
        {
            MessageBox.Show(
                "Не удалось найти Docker Desktop. Установите его с docker.com/products/docker-desktop и повторите проверку.",
                "Docker Desktop не найден",
                MessageBoxButton.OK,
                MessageBoxImage.Information
            );
            return;
        }

        _isBusy = true;
        StartDockerButton.IsEnabled = false;
        DockerEngineStatusText.Text = "Docker Desktop запускается — это может занять до минуты…";

        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(90));
        try
        {
            while (!cancellation.IsCancellationRequested)
            {
                await Task.Delay(TimeSpan.FromSeconds(3), cancellation.Token);
                var result = await _docker.CheckEngineAsync(cancellation.Token);
                if (result.Success)
                {
                    break;
                }
            }
        }
        catch (OperationCanceledException)
        {
            // RefreshChecksAsync will present the final state.
        }
        finally
        {
            _isBusy = false;
            StartDockerButton.IsEnabled = true;
        }

        await RefreshChecksAsync();
    }

    private void InstallDockerButton_Click(object sender, RoutedEventArgs e) =>
        OpenTarget("https://www.docker.com/products/docker-desktop/");

    private void ContinueButton_Click(object sender, RoutedEventArgs e) =>
        ShowPage(LauncherPage.Mode);

    private async void NormalLaunchButton_Click(object sender, RoutedEventArgs e)
    {
        _lastLaunchMode = LaunchMode.Normal;
        await RunLaunchAsync(cleanDatabase: false);
    }

    private async void CleanLaunchButton_Click(object sender, RoutedEventArgs e)
    {
        var answer = MessageBox.Show(
            "Будет удалён только Docker volume проекта и его demo-данные. "
                + "Локальные SQLite-файлы в папке data не изменятся. Продолжить?",
            "Пересоздать demo-базу?",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning
        );
        if (answer != MessageBoxResult.Yes)
        {
            return;
        }

        _lastLaunchMode = LaunchMode.Clean;
        await RunLaunchAsync(cleanDatabase: true);
    }

    private async Task RunLaunchAsync(bool cleanDatabase)
    {
        if (_isBusy || _projectDirectory is null)
        {
            return;
        }

        _isBusy = true;
        _operationCancellation = new CancellationTokenSource();
        ShowProgress("Запускаем проект", "Подготавливаем Docker Compose и большую demo-базу…");
        AppendLog($"> Папка проекта: {_projectDirectory}");

        try
        {
            if (cleanDatabase)
            {
                AppendLog("> docker compose down -v");
                var reset = await _docker.RunAsync(
                    _projectDirectory,
                    AppendLog,
                    _operationCancellation.Token,
                    "compose",
                    "down",
                    "-v"
                );
                if (!reset.Success)
                {
                    ShowFailure("Не удалось очистить Docker demo-базу.");
                    return;
                }
            }

            AppendLog("> docker compose up --build -d");
            var launch = await _docker.RunAsync(
                _projectDirectory,
                AppendLog,
                _operationCancellation.Token,
                "compose",
                "up",
                "--build",
                "-d"
            );
            if (!launch.Success)
            {
                await AppendDiagnosticsAsync();
                ShowFailure("Docker не смог собрать или запустить проект. Подробности находятся в логе.");
                return;
            }

            ProgressStatus.Text = "Контейнеры созданы. Ждём готовности backend и frontend…";
            AppendLog("> Ожидаем http://127.0.0.1:8080/health");
            var ready = await DockerService.WaitForDashboardAsync(
                AppendLog,
                _operationCancellation.Token
            );
            if (!ready)
            {
                await AppendDiagnosticsAsync();
                ShowFailure("Контейнеры запущены, но дашборд не прошёл проверку готовности.");
                return;
            }

            ShowPage(LauncherPage.Ready);
        }
        catch (OperationCanceledException)
        {
            ShowFailure("Запуск отменён. Уже созданные контейнеры можно остановить на итоговом экране.");
        }
        finally
        {
            _operationCancellation?.Dispose();
            _operationCancellation = null;
            _isBusy = false;
        }
    }

    private async Task AppendDiagnosticsAsync()
    {
        if (_projectDirectory is null || _operationCancellation is null)
        {
            return;
        }

        AppendLog("> docker compose ps");
        await _docker.RunAsync(
            _projectDirectory,
            AppendLog,
            _operationCancellation.Token,
            "compose",
            "ps"
        );
        AppendLog("> docker compose logs --tail=80 --no-color");
        await _docker.RunAsync(
            _projectDirectory,
            AppendLog,
            _operationCancellation.Token,
            "compose",
            "logs",
            "--tail=80",
            "--no-color"
        );
    }

    private void ShowProgress(string title, string status)
    {
        ShowPage(LauncherPage.Progress);
        ProgressTitle.Text = title;
        ProgressStatus.Text = status;
        LogTextBox.Clear();
        LaunchProgress.IsIndeterminate = true;
        CancelOperationButton.Visibility = Visibility.Visible;
        RetryButton.Visibility = Visibility.Collapsed;
        ProgressBackButton.Visibility = Visibility.Collapsed;
    }

    private void ShowFailure(string message)
    {
        ProgressTitle.Text = "Нужна небольшая проверка";
        ProgressStatus.Text = message;
        LaunchProgress.IsIndeterminate = false;
        LaunchProgress.Value = 0;
        CancelOperationButton.Visibility = Visibility.Collapsed;
        RetryButton.Visibility = Visibility.Visible;
        ProgressBackButton.Visibility = Visibility.Visible;
    }

    private void AppendLog(string line)
    {
        Dispatcher.InvokeAsync(() =>
        {
            if (LogTextBox.Text.Length > 100_000)
            {
                LogTextBox.Text = LogTextBox.Text[^70_000..];
            }

            LogTextBox.AppendText($"{line}{Environment.NewLine}");
            LogTextBox.ScrollToEnd();
        });
    }

    private void CancelOperationButton_Click(object sender, RoutedEventArgs e) =>
        _operationCancellation?.Cancel();

    private async void RetryButton_Click(object sender, RoutedEventArgs e) =>
        await RunLaunchAsync(_lastLaunchMode == LaunchMode.Clean);

    private void ProgressBackButton_Click(object sender, RoutedEventArgs e) =>
        ShowPage(LauncherPage.Mode);

    private void BackToWelcomeButton_Click(object sender, RoutedEventArgs e) =>
        ShowPage(LauncherPage.Welcome);

    private void BackToCheckButton_Click(object sender, RoutedEventArgs e) =>
        ShowPage(LauncherPage.Check);

    private void ReadyBackButton_Click(object sender, RoutedEventArgs e) =>
        ShowPage(LauncherPage.Mode);

    private void SelectProjectButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Выберите compose.yaml из корня проекта",
            Filter = "Docker Compose (compose.yaml)|compose.yaml|YAML (*.yaml;*.yml)|*.yaml;*.yml",
            FileName = "compose.yaml",
            CheckFileExists = true,
            Multiselect = false,
        };

        if (dialog.ShowDialog(this) != true)
        {
            return;
        }

        var directory = Path.GetDirectoryName(dialog.FileName);
        if (directory is null || !DockerService.IsProjectDirectory(directory))
        {
            MessageBox.Show(
                "В выбранной папке не найдены compose.yaml, docker, frontend и src.",
                "Это не корень проекта",
                MessageBoxButton.OK,
                MessageBoxImage.Information
            );
            return;
        }

        _projectDirectory = directory;
        UpdateProjectPath();
        if (CheckPage.Visibility == Visibility.Visible)
        {
            _ = RefreshChecksAsync();
        }
    }

    private async void StopProjectButton_Click(object sender, RoutedEventArgs e)
    {
        if (_isBusy || _projectDirectory is null)
        {
            return;
        }

        _isBusy = true;
        _operationCancellation = new CancellationTokenSource();
        ShowProgress("Останавливаем проект", "Docker сохраняет demo-базу для следующего запуска…");
        AppendLog("> docker compose down");
        try
        {
            var result = await _docker.RunAsync(
                _projectDirectory,
                AppendLog,
                _operationCancellation.Token,
                "compose",
                "down"
            );
            if (result.Success)
            {
                ProgressTitle.Text = "Проект остановлен";
                ProgressStatus.Text = "Demo-данные сохранены. Проект можно запустить снова в любое время.";
                LaunchProgress.IsIndeterminate = false;
                LaunchProgress.Value = 100;
                CancelOperationButton.Visibility = Visibility.Collapsed;
                ProgressBackButton.Visibility = Visibility.Visible;
            }
            else
            {
                ShowFailure("Docker не смог остановить контейнеры. Проверьте лог.");
            }
        }
        catch (OperationCanceledException)
        {
            ShowFailure("Остановка отменена.");
        }
        finally
        {
            _operationCancellation?.Dispose();
            _operationCancellation = null;
            _isBusy = false;
        }
    }

    private static void OpenTarget(string target)
    {
        try
        {
            DockerService.Open(target);
        }
        catch (Exception exception)
        {
            MessageBox.Show(exception.Message, "Не удалось открыть ссылку");
        }
    }

    private void OpenDashboardButton_Click(object sender, RoutedEventArgs e) => OpenTarget(DashboardUrl);

    private void OpenDocsButton_Click(object sender, RoutedEventArgs e) => OpenTarget(DocsUrl);

    private void UpdateProjectPath()
    {
        ProjectPathText.Text = _projectDirectory is null
            ? "Папка проекта пока не выбрана"
            : _projectDirectory;
        ProjectPathText.ToolTip = _projectDirectory;
    }

    private static void SetPending(
        Border icon,
        TextBlock glyph,
        TextBlock text,
        string message
    )
    {
        icon.Background = new SolidColorBrush(Color.FromRgb(239, 243, 248));
        glyph.Text = "…";
        glyph.Foreground = new SolidColorBrush(Color.FromRgb(100, 116, 139));
        text.Text = message;
    }

    private static void SetCheckResult(
        Border icon,
        TextBlock glyph,
        TextBlock text,
        bool success,
        string successMessage,
        string failureMessage
    )
    {
        icon.Background = new SolidColorBrush(
            success ? Color.FromRgb(229, 247, 237) : Color.FromRgb(255, 237, 238)
        );
        glyph.Text = success ? "✓" : "!";
        glyph.Foreground = new SolidColorBrush(
            success ? Color.FromRgb(22, 132, 71) : Color.FromRgb(194, 65, 74)
        );
        text.Text = success ? successMessage : failureMessage;
    }

    private void ShowPage(LauncherPage page)
    {
        WelcomePage.Visibility = page == LauncherPage.Welcome ? Visibility.Visible : Visibility.Collapsed;
        CheckPage.Visibility = page == LauncherPage.Check ? Visibility.Visible : Visibility.Collapsed;
        ModePage.Visibility = page == LauncherPage.Mode ? Visibility.Visible : Visibility.Collapsed;
        ProgressPage.Visibility = page == LauncherPage.Progress ? Visibility.Visible : Visibility.Collapsed;
        ReadyPage.Visibility = page == LauncherPage.Ready ? Visibility.Visible : Visibility.Collapsed;

        var activeStep = page switch
        {
            LauncherPage.Welcome => 1,
            LauncherPage.Check => 2,
            LauncherPage.Mode or LauncherPage.Progress => 3,
            LauncherPage.Ready => 4,
            _ => 1,
        };
        UpdateSteps(activeStep);
    }

    private void UpdateSteps(int activeStep)
    {
        var rows = new[]
        {
            (StepWelcome, StepWelcomeNumber, StepWelcomeNumberLabel, StepWelcomeLabel),
            (StepCheck, StepCheckNumber, StepCheckNumberLabel, StepCheckLabel),
            (StepMode, StepModeNumber, StepModeNumberLabel, StepModeLabel),
            (StepReady, StepReadyNumber, StepReadyNumberLabel, StepReadyLabel),
        };

        for (var index = 0; index < rows.Length; index++)
        {
            var active = index + 1 == activeStep;
            rows[index].Item1.Background = new SolidColorBrush(
                active ? Color.FromRgb(31, 48, 79) : Colors.Transparent
            );
            rows[index].Item2.Background = new SolidColorBrush(
                active ? Color.FromRgb(44, 107, 255) : Color.FromRgb(38, 54, 83)
            );
            rows[index].Item3.Foreground = new SolidColorBrush(
                active ? Colors.White : Color.FromRgb(170, 183, 206)
            );
            rows[index].Item4.Foreground = new SolidColorBrush(
                active ? Colors.White : Color.FromRgb(170, 183, 206)
            );
            rows[index].Item4.FontWeight = active ? FontWeights.SemiBold : FontWeights.Normal;
        }
    }

    private void Window_Closing(object? sender, CancelEventArgs e) =>
        _operationCancellation?.Cancel();

    private enum LauncherPage
    {
        Welcome,
        Check,
        Mode,
        Progress,
        Ready,
    }

    private enum LaunchMode
    {
        Normal,
        Clean,
    }
}
