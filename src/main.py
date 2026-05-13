import os
import threading
import logging
import queue
import time
from gui import GUI, GUILoggingHandler
from parser import parse_document
from processor import clean_and_format_text

class AppContext:
    def __init__(self):
        self.file_queue = queue.Queue()
        self.gui = None
        self.processing_thread = None
        self.is_running = True

        # We need a separate list just for UI representation since Queue doesn't expose contents safely
        self.ui_queue_list = []

    def add_files(self, files):
        for f in files:
            if f not in self.ui_queue_list:
                self.ui_queue_list.append(f)
                self.file_queue.put(f)
        self.gui.update_queue_list(self.ui_queue_list)
        self._start_processing()

    def remove_queue(self):
        self.ui_queue_list.clear()
        # Empty the queue
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
            except queue.Empty:
                break
        self.gui.update_queue_list(self.ui_queue_list)

    def save_verified(self, title, text, output_dir):
        # Clean title for filesystem
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        filename = safe_title + ".md"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            logging.info(f"Saved verified file to: {filepath}")
        except Exception as e:
            logging.error(f"Failed to save file {filepath}: {e}")

    def _start_processing(self):
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.processing_thread.start()

    def _process_queue(self):
        while self.is_running:
            try:
                current_file = self.file_queue.get(timeout=1.0)
            except queue.Empty:
                if not self.ui_queue_list:
                    break # queue is empty, break out of loop
                continue # loop and check is_running again

            logging.info(f"Processing: {current_file}")
            try:
                # 1. Parse
                raw_text = parse_document(current_file)
                if not raw_text:
                    logging.error(f"Skipping {current_file}: Empty text or parsing failed.")
                    self._pop_and_update(current_file)
                    self.file_queue.task_done()
                    continue

                # 2. Process with DeepSeek
                api_key = self.gui.api_key_var.get().strip()
                title, formatted_text = clean_and_format_text(raw_text, api_key)

                # 3. Add to Pending Verification
                self.gui.after(0, self.gui.add_to_pending, current_file, title, formatted_text)
                logging.info(f"Successfully processed {current_file}. Waiting for verification.")

            except Exception as e:
                logging.error(f"Error processing {current_file}: {e}")

            self._pop_and_update(current_file)
            self.file_queue.task_done()

        logging.info("Batch processing thread resting.")

    def _pop_and_update(self, current_file):
        if current_file in self.ui_queue_list:
            self.ui_queue_list.remove(current_file)
            self.gui.after(0, self.gui.update_queue_list, self.ui_queue_list)

def main():
    ctx = AppContext()

    # Init GUI
    gui = GUI(
        add_files_cb=ctx.add_files,
        save_cb=ctx.save_verified,
        remove_queue_cb=ctx.remove_queue
    )
    ctx.gui = gui

    # Configure logging to route to GUI
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler('app.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # GUI handler
    gui_handler = GUILoggingHandler(gui)
    gui_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(gui_handler)

    logging.info("Application started. Ready to process documents.")

    # Run loop
    try:
        gui.mainloop()
    finally:
        ctx.is_running = False

if __name__ == "__main__":
    main()
