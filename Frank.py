import sys
import ollama
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QProgressBar, QComboBox, QLabel, QLineEdit, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPalette, QColor

class AIThread(QThread):
    update_progress = pyqtSignal(int)
    update_thinking_steps = pyqtSignal(list)
    finished = pyqtSignal(str)

    def __init__(self, prompt, max_iterations, model_name):
        QThread.__init__(self)
        self.prompt = prompt
        self.max_iterations = max_iterations
        self.model_name = model_name
        self.thinking_steps = []

    def run(self):
        final_response = self.recursiveThinking(self.prompt, self.max_iterations)
        self.finished.emit(final_response)

    def primaryAIInput(self, prompt):
        response = ollama.chat(model=self.model_name, messages=[
            {
                'role': 'user',
                'content': prompt
            },
        ])
        return str(response['message']['content'])

    def recursiveThinking(self, initial_prompt, max_iterations):
        def think(prompt, iteration=0):
            if iteration >= max_iterations:
                return prompt

            response = self.primaryAIInput(f"""
You are an AI assistant tasked with providing a thoughtful and comprehensive response to the following prompt:

{initial_prompt}

Your current draft response is:

{prompt}

Carefully analyze this draft. Consider its accuracy, comprehensiveness, and how directly it addresses the original prompt. 
Refine and improve your response, focusing on clarity, conciseness, and addressing all aspects of the prompt.
Do not mention the improvement process or include any meta-commentary about the response.
Simply provide the improved response as if it were your first and only answer to the original prompt.

Refined response:
""")

            self.thinking_steps.append(response)
            self.update_thinking_steps.emit(self.thinking_steps)
            self.update_progress.emit(int((iteration + 1) / max_iterations * 100))

            if response.strip() == prompt.strip():
                return response
            else:
                return think(response, iteration + 1)

        initial_response = self.primaryAIInput(initial_prompt)
        self.thinking_steps.append(initial_response)
        self.update_thinking_steps.emit(self.thinking_steps)
        self.update_progress.emit(int(1 / max_iterations * 100))

        return think(initial_response, 1)

class FrankGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initSystemTray()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Set background color to darker green
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 51, 0))  # Darker green
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Set text color to white for better contrast
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        # Input box
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Enter your prompt here...")
        self.setGrayBackground(self.input_box)
        main_layout.addWidget(QLabel("Input:"))
        main_layout.addWidget(self.input_box)

        # Thinking steps input
        thinking_steps_layout = QHBoxLayout()
        thinking_steps_layout.addWidget(QLabel("Number of thinking steps:"))
        self.thinking_steps_input = QLineEdit()
        self.thinking_steps_input.setText("3")  # Default value
        self.setGrayBackground(self.thinking_steps_input)
        thinking_steps_layout.addWidget(self.thinking_steps_input)
        main_layout.addLayout(thinking_steps_layout)

        # AI model input
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI Model:"))
        self.model_input = QLineEdit()
        self.model_input.setText("llama3.1")  # Default value
        self.setGrayBackground(self.model_input)
        model_layout.addWidget(self.model_input)
        main_layout.addLayout(model_layout)

        # Process button
        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(self.process_input)
        self.setGrayBackground(self.process_button)
        main_layout.addWidget(self.process_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.setGrayBackground(self.progress_bar)
        main_layout.addWidget(self.progress_bar)

        # Thinking steps dropdown
        self.thinking_steps_dropdown = QComboBox()
        self.thinking_steps_dropdown.currentIndexChanged.connect(self.update_output)
        self.setGrayBackground(self.thinking_steps_dropdown)
        main_layout.addWidget(QLabel("Thinking Steps:"))
        main_layout.addWidget(self.thinking_steps_dropdown)

        # Output box
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.setGrayBackground(self.output_box)
        main_layout.addWidget(QLabel("Output:"))
        main_layout.addWidget(self.output_box)

        # Create a widget to hold the main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        # Create a layout for the central widget
        wrapper_layout = QVBoxLayout()
        wrapper_layout.addWidget(central_widget)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(wrapper_layout)
        self.setWindowTitle('Frank')
        self.setGeometry(300, 300, 600, 500)

        self.thinking_steps = []

    def setGrayBackground(self, widget):
        palette = widget.palette()
        palette.setColor(QPalette.Base, QColor(89, 89, 89))  # Gray
        palette.setColor(QPalette.Text, Qt.black)  # Black text for contrast
        widget.setPalette(palette)

    def initSystemTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('icon.ico'))  # Make sure to have an icon file

        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Frank",
            "Application was minimized to the system tray",
            QSystemTrayIcon.Information,
            2000
        )

    def process_input(self):
        prompt = self.input_box.toPlainText()
        try:
            max_iterations = int(self.thinking_steps_input.text())
        except ValueError:
            max_iterations = 3  # Default if invalid input
        model_name = self.model_input.text()

        self.progress_bar.setValue(0)
        self.thinking_steps_dropdown.clear()
        self.output_box.clear()
        self.thinking_steps = []

        self.thread = AIThread(prompt, max_iterations, model_name)
        self.thread.update_progress.connect(self.update_progress)
        self.thread.update_thinking_steps.connect(self.update_thinking_steps)
        self.thread.finished.connect(self.process_finished)
        self.thread.start()

        self.process_button.setEnabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_thinking_steps(self, steps):
        self.thinking_steps = steps
        self.thinking_steps_dropdown.clear()
        for i in range(len(steps)):
            self.thinking_steps_dropdown.addItem(f"Step {i+1}")
        self.thinking_steps_dropdown.setCurrentIndex(len(steps) - 1)

    def update_output(self, index):
        if 0 <= index < len(self.thinking_steps):
            self.output_box.setPlainText(self.thinking_steps[index])

    def process_finished(self, result):
        self.process_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    ex = FrankGUI()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()