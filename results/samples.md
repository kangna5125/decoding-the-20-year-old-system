### parse_hgnc_genes
```python
def parse_hgnc_genes(lines):
    header = []
    logger.info("Parsing hgnc genes...")
    for index, line in enumerate(lines):
        if index == 0:
            header = line.split('\t')
        elif len(line) > 1:
            hgnc_gene = parse_hgnc_line(line=line, header=header)
```
- Real description: Parse lines with hgnc formated genes
- Model: Parse hgnc genes.
- Confidence: 59%
- Source: https://github.com/Clinical-Genomics/scout/blob/90a551e2e1653a319e654c2405c2866f93d0ebb9/scout/parse/hgnc.py#L88-L108

### ContinuedLineState.push_token
```python
def push_token(self, token, position):
        if _token_followed_by_eol(self._tokens, position):
            self._cont_stack.append(self._hanging_indent_after_bracket(token, position))
        else:
            self._cont_stack.append(self._continuation_inside_bracket(token, position))
```
- Real description: Pushes a new token for continued indentation on the stack.
- Model: Push a token to the end of the stack.
- Confidence: 57%
- Source: https://github.com/PyCQA/pylint/blob/2bf5c61a3ff6ae90613b81679de42c0f19aea600/pylint/checkers/format.py#L559-L576

### institute_and_case
```python
def institute_and_case(store, institute_id, case_name=None):
    institute_obj = store.institute(institute_id)
    if institute_obj is None and institute_id != 'favicon.ico':
        flash("Can't find institute: {}".format(institute_id), 'warning')
        return abort(404)

    if case_name:
        if case_name:
```
- Real description: Fetch insitiute and case objects.
- Model: Get institute and case information.
- Confidence: 53%
- Source: https://github.com/Clinical-Genomics/scout/blob/90a551e2e1653a319e654c2405c2866f93d0ebb9/scout/server/utils.py#L33-L59

### SignalManager.action
```python
def action(self, arg):
        if not arg:
            self.info_signal(['handle'])
            return True
        args = arg.split()
        signame = args[0]
        signame = self.is_name_or_number(args[0])
        if not signame: return
```
- Real description: Delegate the actions specified in 'arg' to another method.
- Model: Handle a command.
- Confidence: 41%
- Source: https://github.com/rocky/python3-trepan/blob/14e91bc0acce090d67be145b1ac040cab92ac5f3/trepan/lib/sighandler.py#L342-L387

### utcnow
```python
def utcnow():

    # pendulum utcnow() is not used as that sets a TimezoneInfo object
    # instead of a Timezone. This is not pickable and also creates issues
    # when using replace()
    d = dt.datetime.utcnow()
    d = d.replace(tzinfo=utc)

```
- Real description: Get the current date and time in UTC :return:
- Model: Returns a datetime object representing the utcnow time.
- Confidence: 43%
- Source: https://github.com/apache/airflow/blob/b69c686ad8a0c89b9136bb4b31767257eb7b2597/airflow/utils/timezone.py#L52-L64

### _maybe_host_form_to_py_ast
```python
def _maybe_host_form_to_py_ast(
    _: GeneratorContext, node: MaybeHostForm
) -> GeneratedPyAST:
    assert node.op == NodeOp.MAYBE_HOST_FORM
    return GeneratedPyAST(
        node=_load_attr(
            f"{Maybe(_MODULE_ALIASES.get(node.class_)).or_else_get(node.class_)}.{node.field}"
        )
```
- Real description: Generate a Python AST node for accessing a potential Python module variable name with a namespace.
- Model: Convert a MaybeHostForm node to a GeneratedPyAST.
- Confidence: 64%
- Source: https://github.com/chrisrink10/basilisp/blob/3d82670ee218ec64eb066289c82766d14d18cc92/src/basilisp/lang/compiler/generator.py#L1941-L1951

### Filterbank.plot_spectrum_min_max
```python
def plot_spectrum_min_max(self, t=0, f_start=None, f_stop=None, logged=False, if_id=0, c=None, **kwargs):
        ax = plt.gca()

        plot_f, plot_data = self.grab_data(f_start, f_stop, if_id)

        #Using accending frequency for all plots.
        if self.header[b'foff'] < 0:
            plot_data = plot_data[..., ::-1] # Reverse data
```
- Real description: Plot frequency spectrum of a given file
- Model: Plot the spectrum minimum and maximum frequency.
- Confidence: 41%
- Source: https://github.com/UCBerkeleySETI/blimpy/blob/b8822d3e3e911944370d84371a91fa0c29e9772e/blimpy/filterbank.py#L578-L642

### U2Gate.to_matrix
```python
def to_matrix(self):
        isqrt2 = 1 / numpy.sqrt(2)
        phi, lam = self.params
        phi, lam = float(phi), float(lam)
        return numpy.array([[isqrt2, -numpy.exp(1j * lam) * isqrt2],
                            [
                                numpy.exp(1j * phi) * isqrt2,
                                numpy.exp(1j * (phi + lam)) * isqrt2
```
- Real description: Return a Numpy.array for the U3 gate.
- Model: Return a matrix representation of this object.
- Confidence: 39%
- Source: https://github.com/Qiskit/qiskit-terra/blob/d4f58d903bc96341b816f7c35df936d6421267d1/qiskit/extensions/standard/u2.py#L44-L54

### Segmenter.processFlat
```python
def processFlat(self):
        # Preprocess to obtain features, times, and input boundary indeces
        F = self._preprocess()

        # Normalize
        F = U.normalize(F, norm_type=self.config["label_norm_feats"],
                        floor=self.config["label_norm_floor"],
                        min_db=self.config["label_norm_min_db"])
```
- Real description: Main process. Returns ------- est_idx : np.array(N) Estimated indeces for the segment boundaries in frames. est_labels : np.array(N-1) Estimated labels for the segments.
- Model: Process a flat dataset.
- Confidence: 38%
- Source: https://github.com/urinieto/msaf/blob/9dbb57d77a1310465a65cc40f1641d083ca74385/msaf/algorithms/fmc2d/segmenter.py#L181-L209

### RequirementSet.cleanup_files
```python
def cleanup_files(self):
        logger.debug('Cleaning up...')
        with indent_log():
            for req in self.reqs_to_cleanup:
                req.remove_temporary_source()

            if self._pip_has_created_build_dir():
                logger.debug('Removing temporary dir %s...', self.build_dir)
```
- Real description: Clean up files, remove builds.
- Model: Clean up all temporary files.
- Confidence: 46%
- Source: https://github.com/tnkteja/myhelp/blob/fb3a4809d448ad14d5b2e6ddf2e7e89ad52b71cb/virtualEnvironment/lib/python2.7/site-packages/pip/req/req_set.py#L461-L470

### BaseAdaptorField.empty_value
```python
def empty_value(self):
        edit_empty_value = self.config.get('edit_empty_value', False)
        if edit_empty_value:
            return edit_empty_value
        else:
            return unicode(inplace_settings.INPLACEEDIT_EDIT_EMPTY_VALUE)
```
- Real description: Get the text to display when the field is empty.
- Model: Returns the value of the empty edit.
- Confidence: 49%
- Source: https://github.com/django-inplaceedit/django-inplaceedit/blob/7ba18e7906f56c56395ca07e2486755062efce00/inplaceeditform/fields.py#L143-L151

### CHNMF.factorize
```python
def factorize(self, show_progress=False, compute_w=True, compute_h=True,
                  compute_err=True, niter=1):

        AA.factorize(self, niter=1, show_progress=show_progress,
                  compute_w=compute_w, compute_h=compute_h,
                  compute_err=compute_err)
```
- Real description: Factorize s.t. WH = data
- Model: Factorize the model.
- Confidence: 40%
- Source: https://github.com/urinieto/msaf/blob/9dbb57d77a1310465a65cc40f1641d083ca74385/msaf/pymf/chnmf.py#L193-L218

### SSHKey.parse_options
```python
def parse_options(self, options):
        quote_open = False
        parsed_options = {}

        def parse_add_single_option(opt):
            """Parses and validates a single option, and adds it to parsed_options field."""
            if "=" in opt:
                opt_name, opt_value = opt.split("=", 1)
```
- Real description: Parses ssh options string.
- Model: Parses a list of options and parses it into a dictionary.
- Confidence: 55%
- Source: https://github.com/ojarva/python-sshpubkeys/blob/86dc1ab27ce82dcc091ce127416cc3ee219e9bec/sshpubkeys/keys.py#L251-L295

### MultiplexingCommandLocator.removeFactory
```python
def removeFactory(self, identifier):
        factory = self._factories.pop(identifier)
        factory.doStop()
        return factory
```
- Real description: Removes a factory.
- Model: Removes a factory from the registry.
- Confidence: 63%
- Source: https://github.com/lvh/txampext/blob/a7d6cb9f1e9200dba597378cd40eb6a2096d4fd9/txampext/multiplexing.py#L112-L123

### get
```python
def get(url,headers=None,token=None,data=None,return_json=True):
    bot.debug("GET %s" %url)
    return call(url,
                headers=headers,
                func=requests.get,
                data=data,
                return_json=return_json)
```
- Real description: get will use requests to get a particular url
- Model: Get data from a URL.
- Confidence: 43%
- Source: https://github.com/singularityhub/sregistry-cli/blob/abc96140a1d15b5e96d83432e1e0e1f4f8f36331/sregistry/main/workers/tasks.py#L84-L92

