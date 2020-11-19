import numpy as np


class Vector:
    """
    Класс вектор
    """
    def __init__(self, *args):
        """
        Инициализация вектора. Задаётся через последовательное введение его координат
        :param args: список координат вектора
        """
        self.size = len(args)  # размер вектора
        self.vector = np.array(args)  # объект вектора, введённый через массив numpy

    def norm(self):
        """
        Возвращает норму вектора
        :return: норма вектора
        """
        return np.linalg.norm(self.vector)

    def multiply_by_constant(self, a):
        """
        Умножение на скаляр
        :param a: скаляр
        :return: результат умножения
        """
        return self.vector * a

    def add_vector(self, other):
        """
        Возвращает результат сложения двух векторов
        :param other: вектор, который прибавляем к данному
        :return: результат сложения
        """
        return self.vector + other.vector

    def scalar_multiplication(self, other):
        """
        Скалярное умножение двух векторов
        :param other: вектор, на которых скалярно умножаем
        :return: результат умножения
        """
        return self.vector @ other.vector

    def vector_multiplication(self, other):
        """
        Векторное произведение векторов
        :param other: вектор, на который векторно умножаем
        :return: результат произведения векторов
        """
        return np.cross(self.vector, other.vector)

    def distance_between_vectors(self, other):
        """
        Расстояние между векторами
        :param other: вектор, до которого рассчитываем расстояние
        :return: расстояние между векторами
        """
        return np.linalg.norm(self.vector - other.vector)

    def multiply_with_matrix(self, matrix_, other):
        """
        Умножение на вектор с помощью матрицы
        :param matrix_: матрица, которую используем для умножения
        :param other: вектор на который умножаем
        :return: результат умножения
        """
        return (self.vector * matrix_) @ other.vector


# Создаём вектора
V1 = Vector(1, 2, 3)
V2 = Vector(2, 3, 4)

print("Вектор 1", V1.vector)
print("Вектор 2", V2.vector)
print("Норма вектора 1 = ", V1.norm())
print("Умножение на скаляр", V1.multiply_by_constant(5))
print("Сложением векторов", V1.add_vector(V2))
print("Скалярное умножение", V1.scalar_multiplication(V2))
print("Векторное умножение", V1.vector_multiplication(V2))
print("Расстояние между векторами", V1.distance_between_vectors(V2))
print("Умножение векторов через матрицу", V1.multiply_with_matrix(np.array(range(9)).reshape(3, 3),
                                                                  Vector(1, 1, 1)))
