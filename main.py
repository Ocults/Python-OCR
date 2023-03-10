import os
import subprocess
import pandas as pd
import pytesseract
from PIL import Image
from pytesseract import Output


def capture_screenshot():
    result = subprocess.run(
        ["maim", "-u", "-f", "png", "-s", "-b", "2", "/var/tmp/ocr.png"],
        stdout=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        print("The command was executed successfully.")
        return "/var/tmp/ocr.png"
    else:
        os.system(f"notify-send 'Screenshot aborted.'")
        print("The command failed.")
        return None


def extract_text_from_image(image_path):
    custom_config = r"-c preserve_interword_spaces=1 --oem 3 --psm 6 -l eng"
    d = pytesseract.image_to_data(
        Image.open(image_path), config=custom_config, output_type=Output.DICT
    )
    df = pd.DataFrame(d)

    # clean up blanks
    df1 = df[(df.conf != "-1") & (df.text != " ") & (df.text != "")]

    # sort blocks vertically
    sorted_blocks = df1.groupby("block_num").first().sort_values("top").index.tolist()

    text = ""
    for block in sorted_blocks:
        curr = df1[df1["block_num"] == block]
        sel = curr[curr.text.str.len() > 3]
        char_w = (sel.width / sel.text.str.len()).mean()
        prev_par, prev_line, prev_left = 0, 0, 0
        for ix, ln in curr.iterrows():
            # add new line when necessary
            if prev_par != ln["par_num"]:
                text += "\n"
                prev_par = ln["par_num"]
                prev_line = ln["line_num"]
                prev_left = 0
            elif prev_line != ln["line_num"]:
                text += "\n"
                prev_line = ln["line_num"]
                prev_left = 0

            added = 0  # num of spaces that should be added
            if ln["left"] / char_w > prev_left + 1:
                added = int((ln["left"]) / char_w) - prev_left
                text += " " * added
            text += ln["text"] + " "
            prev_left += len(ln["text"]) + added + 1
        text += "\n"

    return text.strip()


def copy_to_clipboard(text):
    process = subprocess.Popen(["xclip", "-selection", "c"], stdin=subprocess.PIPE)
    process.communicate(input=text.encode())


def main():
    image_path = capture_screenshot()
    text = extract_text_from_image(image_path)
    print(text)
    copy_to_clipboard(text)
    os.system(f"notify-send 'Copied to clipboard.'")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        os.system("notify-send 'Cancelled.'")
