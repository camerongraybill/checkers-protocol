from unittest import TestCase

from server.queue import UserQueue, NotInQueue, DuplicateUser, QueueTooSmall


class TestQueue(TestCase):
    class ASession:
        def __init__(self, rating):
            self.rating = rating

        def __eq__(self, other):
            return self.rating == other.rating

    def test_normal_use(self):
        user_one = TestQueue.ASession(2)
        user_two = TestQueue.ASession(4)
        user_three = TestQueue.ASession(5)

        q = UserQueue()
        q.enqueue_user(user_one)
        q.enqueue_user(user_two)
        q.enqueue_user(user_three)

        self.assertListEqual([user_two, user_three], list(q.pop_closest_pair()))
        self.assertEqual(0, q.location_of(user_one))

    def test_exceptional_cases(self):
        user_one = self.ASession(2)

        q = UserQueue()

        with self.assertRaises(NotInQueue):
            q.dequeue_user(user_one)

        with self.assertRaises(QueueTooSmall):
            q.pop_closest_pair()

        q.enqueue_user(user_one)

        with self.assertRaises(QueueTooSmall):
            q.pop_closest_pair()

        with self.assertRaises(DuplicateUser):
            q.enqueue_user(user_one)

        q.dequeue_user(user_one)

        with self.assertRaises(NotInQueue):
            q.location_of(user_one)
