from Window import *
from pathlib import Path

import cv2
import numpy as np
import imutils
import os
import logging as l

class OpenCV:
    """
    Class used for extracting information from the window the 
    Minesweeper game is currently running in by performing 
    template matching.
    """

    _unchecked_window_name = "Unchecked Window Result"
    _checked_window_name = "Checked Window Result"

    _template_paths = {
        "udark": "resources/squares_unchecked/square_dark.png",
        "umedium": "resources/squares_unchecked/square_medium.png",
        "ulight": "resources/squares_unchecked/square_light.png",
        "c0": "resources/squares_checked/square_empty.png",
        "c1": "resources/squares_checked/square_1.png",
        "c2": "resources/squares_checked/square_2.png",
        "c3": "resources/squares_checked/square_3.png",
        "c4": "resources/squares_checked/square_4.png",
        "c5": "resources/squares_checked/square_5.png",
        "c6": "resources/squares_checked/square_6.png",
        "c7": "resources/squares_checked/square_7.png",
        "c8": "resources/squares_checked/square_8.png",
    }

    # {key: template, ...}
    _templates = {}
    _threshold = 0.8

    def __init__(self):
        self.load_templates()

    def load_templates(self):
        """
        Function for loading the templates from the resource folder.
        """

        self._templates.clear()
        current_dir = os.getcwd()

        l.info("Loading templates...")

        # Check all paths and their corresponding templates.
        for key, path in self._template_paths.items():
            try:
                complete_path = str(Path(current_dir) / path)
                template = cv2.imread(complete_path, 0)
                
                l.debug(f"- {path}")
                self._templates[key] = template
            except Exception as e:
                l.error(f"Exception while loading {path}: {e}")

    def update_result_windows(self, unchecked_result_image, checked_result_image):
        """
        Function for updating the windows showing the results of 
        the different template matchings.
        """

        cv2.imshow(self._unchecked_window_name, unchecked_result_image)
        cv2.imshow(self._checked_window_name, checked_result_image)
        cv2.waitKey()

    def prepare_image(self, image):
        """
        Function for converting a taken screenshot of the game's
        window into a usable form.
        """

        # Convert PIL image to opencv one.
        open_cv_image = np.array(image) 
        # Convert RGB to BGR 
        open_cv_image = open_cv_image[:, :, ::-1].copy() 
        # Grayscale the image in order to work with the loaded template.
        gray_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

        return (open_cv_image, gray_image)

    def is_finished(self, image):
        pass

    def get_field_information(self, image):
        """
        Function for extracting the game information (values, bombs, checked / unchecked)
        from a provided image.
        """

        # TODO: Replace with correct implementation.
        key = "udark"
        template = self._templates[key]
        width, height = template.shape[::-1]

        # Use the opencv template matching for finding the desired points.
        open_cv_image, gray_image = self.prepare_image(image)
        points, ratio = self.match_scaling_with_template(key, gray_image)
        filtered_points = self.filter_points(points, width, height)

        # Adjust the results based on the ratio between the image and the template.
        adjusted_squares, centers = self.adjust_values_based_on_ratio(filtered_points, ratio, width, height)

        # Display the results in a window to verify them.
        self.display_field_results(open_cv_image, adjusted_squares, centers)

    def display_field_results(self, open_cv_image, adjusted_squares, centers):
        """
        Function for displaying the generated results in a single window.
        """

        for rect in adjusted_squares:
            cv2.rectangle(open_cv_image, rect[0], rect[1], (0, 0, 255), 1)
        for center in centers:
            radius = 2
            circle_center = (center[0] - radius // 2, center[1] - radius // 2)
            cv2.circle(open_cv_image, circle_center, radius, (255, 0, 0), -1)

        # Display the results in a single window.
        cv2.imshow(self._unchecked_window_name, open_cv_image)
        cv2.waitKey()

    def extract_unchecked(self, image):
        pass

    def extract_checked(self, image):
        pass

    def match_scaling_with_template(self, template_key, gray_image):
        """
        Function for matching the image with the template accessible by 
        the provided template_key. This function scales the image in 
        order to match different window sizes with the same template.
        returns:
        ([points], ratio)
        """

        best_matching = None
        template = self._templates[template_key]
        template_height, template_width = template.shape[:2]

        # Gradually scale the image down.
        for scale in np.linspace(0.1, 1.0, 30)[::-1]:
            # Resize the image in order to match the template's size.
            # shape[1] is the width of the image
            resized_gray_image = imutils.resize(gray_image, int(gray_image.shape[1] * scale))
            ratio = gray_image.shape[1] / float(resized_gray_image.shape[1])

            # Image must not be smaller than the template.
            if resized_gray_image.shape[0] < template_height or resized_gray_image.shape[1] < template_width:
                break

            # Template matching.
            result = cv2.matchTemplate(resized_gray_image, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= self._threshold)
            points = list(zip(*locations[::-1]))

            # All of the squares must be matched (Error prone!).
            if best_matching is None or len(best_matching[0]) < len(points):
                best_matching = points, ratio

        l.debug("Best matching: {} points, {} ratio".format(len(best_matching[0]), best_matching[1]))
        return best_matching

    def filter_points(self, points, width, height):
        """
        Fuction for filtering the points based on the distance to one another 
        such that only a single point for each square remains.
        """

        l.info("Filering points...")
        l.debug("{} points found.".format(len(points)))

        # Filter the points in such a way that only one point per square remains.
        # Highly inefficient (O(N^2)), but it works.
        filtered_points = []
        for point in points:
            result = True
            if len(filtered_points) > 0:
                point_array = np.array(point)
                for other_point in filtered_points:
                    other_point_array = np.array(other_point)
                    distance = np.linalg.norm(point_array - other_point_array)
                    # Only a single point can remain per square since the distance would otherwise be too small.
                    if distance < min(width, height):
                        result = False
            if result:
                filtered_points.append(point)

        l.debug("{} points remain after filtering.".format(len(filtered_points)))
        return filtered_points

    def adjust_values_based_on_ratio(self, points, ratio, width, height):
        """
        Function for adjusting the existing template's values based on a 
        returned ratio. The points and sizes received from the template 
        matching must be changed to match the base image dimensions. A 
        template matching a region of the image while the latter is scaled 
        down must be scaled up in order to properly match it again.
        """
        
        adjusted_points = map(lambda point: (int(point[0] * ratio), int(point[1] * ratio)), points)
        adjusted_width = int(width * ratio)
        adjusted_height = int(height * ratio)
        # Top left and bottom right are saved in order to display a rectangle.
        adjusted_squares = map(lambda point: (point, (point[0] + adjusted_width, point[1] + adjusted_height)), adjusted_points)

        centers = list(map(lambda point: (point[0] + adjusted_width // 2, point[1] + adjusted_height // 2), adjusted_points))

        return list(adjusted_squares), centers