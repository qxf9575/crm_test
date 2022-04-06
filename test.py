

# class A:
#     def func(self):
#         print(1)
#
#
#
# a = A()
# print(a.func)
# getattr(a,'func')()



#
# class F:
#     def __init__(self, name):
#         self.name = name
#
#     def __getattr__(self, item):
#         return '__getattr__'
#
# obj = F('tom')
# print(obj.name)
# print(obj.age)