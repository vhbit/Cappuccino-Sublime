import sublime, sublime_plugin
import os.path
import re

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

    BUILTIN_TYPES = [
        ("id", "id"),
        ("int", "int"),
        ("BOOL", "BOOL"),
        ("void", "void")
    ]

    SOURCE_RE = re.compile(r'^[a-z](\w|\n|\s)*\.j$', re.I)

    def filter_duplicates(self, completions, prefix):
        return list(set([comp for comp in completions if comp[0].find(prefix) == 0]))

    def on_query_completions(self, view, prefix, locations):
        if not view.settings().get("syntax").endswith("/Objective-J.tmLanguage") or len(locations) > 1:
            return []

        location = locations[0]
        completions = []

        # See if we are in a bracketed scope
        scopes = view.scope_name(location).split()

        print "Scopes are: ", scopes

        if ("meta.return-type.js.objj" in scopes) or ("meta.argument-type.js.objj" in scopes) or ("meta.scope.instance-variables.js.objj" in scopes):
            self.append_completions("classes", completions, prefix)
            self.append_builtin_types(completions)

            if "meta.return-type.js.objj" is scopes:
                self.append_explicit_completion(completions, "@action")
            if "meta.instance-variables.js.objj" is scopes:
                self.append_explicit_completion(completions, "@outlet")
        elif "meta.import.js.objj" in scopes:
            relPathEndLocation = -1

            while location >= 0:
                location -= 1
                ch = view.substr(location)
                if ch == '/' and relPathEndLocation == -1:
                    relPathEndLocation = location
                elif ch in ['<', '"']:
                    break

            # Go forward to the first character after the start of name
            # and get the next word
            location += 1

            if relPathEndLocation == -1:
                relPath = ''
            else:
                relPathRegion = sublime.Region(location, relPathEndLocation)
                relPathWords = view.word(relPathRegion)
                relPath = view.substr(relPathWords)

            region = view.word(location)
            dir = view.substr(region)
            print dir, prefix

            for sourcePath in view.settings().get('objj_src_paths'):
                root = os.path.join(sourcePath, relPath)
                if os.path.isdir(root):
                    if os.path.isdir(os.path.join(root, prefix)):
                        self.append_explicit_completion(completions, prefix + '/')
                    else:
                        candidates = os.listdir(root)
                        for candidate in candidates:
                            if candidate in ['.', '..']:
                                continue
                            fullPath = os.path.join(root, candidate)
                            if os.path.isdir(fullPath):
                                completions.append((candidate, candidate + '/',))
                            elif os.path.isfile(fullPath) and self.SOURCE_RE.match(candidate):
                                self.append_explicit_completion(completions, candidate)
        else:
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
                if len(symbol) > 3 and self.is_class_name(symbol)[0]:
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
                    print 'Instance method case'
                    return self.filter_duplicates(completions, prefix)

                # If we get here, we are in a bracketed scope, which means instance methods are valid
                self.append_completions("instance_methods", completions, prefix)
            print 'general case'
            # If we get here, add everything but class/instance methods
            self.append_completions("classes", completions, prefix)
            self.append_completions("functions", completions, prefix)
            self.append_completions("constants", completions, prefix)
        return self.filter_duplicates(completions, prefix)

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

    def append_builtin_types(self, completions):
        completions.extend(self.BUILTIN_TYPES)

    def append_explicit_completion(self, completions, completion):
        completions.append((completion, completion,))

    def append_completions(self, symbolType, completions, prefix):
        print "append_completions({0})".format(symbolType)
        path = os.path.join(self.LIB_PATH, symbolType + ".completions")

        if os.path.exists(path):
            try:
                localVars = {}
                execfile(path, globals(), localVars)
                symbolCompletions = localVars["completions"]
                completions.extend(symbolCompletions)
                #completions += [comp for comp in symbolCompletions if comp[0].find(prefix) == 0]
            except Exception as ex:
                print ex
                pass
