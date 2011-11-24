import sublime, sublime_plugin
import os.path

class CappuccinoCompletions(sublime_plugin.EventListener):
    LIB_PATH = os.path.join(sublime.packages_path(), "Objective-J", "lib")
    CLASS_METHODS_PATH = os.path.join(LIB_PATH, "class_methods")
    DIVIDER = "-------- {0} -------"
    SYMBOL_SUFFIXES = {
        "classes": " [c]",
        "constants": " [k]",
        "functions": "()",
        "instance_methods": " [m]"
    }

    def filter_duplicates(self, completions):
        return list(set(completions))

    def on_query_completions(self, view, prefix, locations):
        if not view.settings().get("syntax").endswith("/Objective-J.tmLanguage") or len(locations) > 1:
            return []

        location = locations[0]
        completions = []

        # See if we are in a bracketed scope
        scopes = view.scope_name(location).split()

        if "meta.bracketed.js.objj" in scopes:
            # Go back until we find the closest open bracket
            while True:
                location -= 1
                
                if view.substr(location) == "[":
                    break

            # Go forward to the first character after the [
            # and get the next word
            location += 1
            region = view.word(location)
            symbol = view.substr(region)
            
            # We are looking for a class name, which must be at least
            # 3 characters (2 character prefix + name) and must be a valid Cappuccino class.
            if len(symbol) > 2 and self.is_class_name(symbol)[0]:
                prefix = prefix.lower()

                while True:
                    superclass, classCompletions = self.read_class_methods(symbol, prefix)

                    # Filter out duplicates
                    for index in range(len(classCompletions) - 1, -1, -1):
                        signature = classCompletions[index][0]

                        if filter(lambda x: x[0] == signature, completions):
                            del classCompletions[index]

                    if len(classCompletions):
                        completions += classCompletions

                    if superclass:
                        symbol = superclass
                    else:
                        break                
                return self.filter_duplicates(completions)

            # If we get here, we are in a bracketed scope, which means instance methods are valid
            self.append_completions("instance_methods", completions, prefix)

        # If we get here, add everything but class/instance methods
        self.append_completions("classes", completions, prefix)
        self.append_completions("functions", completions, prefix)
        self.append_completions("constants", completions, prefix)
        return self.filter_duplicates(completions)

    def is_class_name(self, name):
        if not hasattr(self, "classes_dict"):
            path = os.path.join(self.LIB_PATH, 'classes.completions')
            self.classes_dict = {}
            try:
                localVars = {}
                execfile(path, globals(), localVars)
                classesCompletions = localVars["completions"]
                if classesCompletions:
                    self.classes_dict = dict([(completion[0], True) for completion in classesCompletions])
            except Exception as ex:
                print ex
                pass

        return (self.classes_dict.has_key(name),  os.path.join(self.CLASS_METHODS_PATH, name + ".completions"))
                
    def read_class_methods(self, className, prefix):
        print "read_class_methods({0})".format(className)
        isClassName, path = self.is_class_name(className)

        if isClassName:
            try:
                localVars = {}
                execfile(path, globals(), localVars)
                return (localVars["superclass"], localVars["completions"] or [])
            except Exception as ex:
                print ex
                pass
        
        return ("", [])

    def append_completions(self, symbolType, completions, prefix):
        print "append_completions({0})".format(symbolType)
        path = os.path.join(self.LIB_PATH, symbolType + ".completions")

        if os.path.exists(path):
            try:
                localVars = {}
                execfile(path, globals(), localVars)
                symbolCompletions = localVars["completions"]

                completions += [comp for comp in symbolCompletions if comp[0].find(prefix) >= 0]
            except Exception as ex:
                print ex
                pass
