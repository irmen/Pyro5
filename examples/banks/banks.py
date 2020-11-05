from Pyro5.api import expose, behavior


# Unrestricted account.
class Account(object):
    def __init__(self):
        """
        Initialize the balance.

        Args:
            self: (todo): write your description
        """
        self._balance = 0.0

    def withdraw(self, amount):
        """
        Withdraw a amount to the given amount.

        Args:
            self: (todo): write your description
            amount: (int): write your description
        """
        self._balance -= amount

    def deposit(self, amount):
        """
        Deprecated

        Args:
            self: (todo): write your description
            amount: (int): write your description
        """
        self._balance += amount

    def balance(self):
        """
        Return the balance of the balance.

        Args:
            self: (todo): write your description
        """
        return self._balance


# Restricted withdrawal account.
class RestrictedAccount(Account):
    def withdraw(self, amount):
        """
        Withdraw balance.

        Args:
            self: (todo): write your description
            amount: (int): write your description
        """
        if amount <= self._balance:
            self._balance -= amount
        else:
            raise ValueError('insufficent balance')


# Abstract bank.
@expose
@behavior(instance_mode="single")
class Bank(object):
    def __init__(self):
        """
        Initialize the account.

        Args:
            self: (todo): write your description
        """
        self.accounts = {}

    def name(self):
        """
        Returns the name.

        Args:
            self: (todo): write your description
        """
        pass  # must override this!

    def createAccount(self, name):
        """
        Creates a new account.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        pass  # must override this!

    def deleteAccount(self, name):
        """
        Deletes an account.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        try:
            del self.accounts[name]
        except KeyError:
            raise KeyError('unknown account')

    def deposit(self, name, amount):
        """
        Returns the amount of amount to the amount instead.

        Args:
            self: (todo): write your description
            name: (str): write your description
            amount: (int): write your description
        """
        try:
            return self.accounts[name].deposit(amount)
        except KeyError:
            raise KeyError('unknown account')

    def withdraw(self, name, amount):
        """
        Withdraw a amount by amount.

        Args:
            self: (todo): write your description
            name: (str): write your description
            amount: (int): write your description
        """
        try:
            return self.accounts[name].withdraw(amount)
        except KeyError:
            raise KeyError('unknown account')

    def balance(self, name):
        """
        Returns the balance of the given account.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        try:
            return self.accounts[name].balance()
        except KeyError:
            raise KeyError('unknown account')

    def allAccounts(self):
        """
        Returns all accounts of accounts.

        Args:
            self: (todo): write your description
        """
        accs = {}
        for name in self.accounts.keys():
            accs[name] = self.accounts[name].balance()
        return accs


# Special bank: Rabobank. It has unrestricted accounts.
@expose
class Rabobank(Bank):
    def name(self):
        """
        Return the name for this node.

        Args:
            self: (todo): write your description
        """
        return 'Rabobank'

    def createAccount(self, name):
        """
        Creates a new account.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        if name in self.accounts:
            raise ValueError('Account already exists')
        self.accounts[name] = Account()


# Special bank: ABN. It has restricted accounts.
@expose
class ABN(Bank):
    def name(self):
        """
        Return the name for this node.

        Args:
            self: (todo): write your description
        """
        return 'ABN bank'

    def createAccount(self, name):
        """
        Creates a new account.

        Args:
            self: (todo): write your description
            name: (str): write your description
        """
        if name in self.accounts:
            raise ValueError('Account already exists')
        self.accounts[name] = RestrictedAccount()
